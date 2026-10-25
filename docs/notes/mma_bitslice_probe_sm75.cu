// TensorFold-style bit-stability probe for TU104 / SM75 (2026-09-27) — v2
//
// Follows TensorFold's kernel-design discipline (github.com/ashhart/TensorFold,
// kernels/qwen/dense/v1/simd_qmm.py): their "exact lane decoder" rests on one
// empirical, per-architecture fact — on an M3 Ultra, an fp32 MMA equals the forward
// FMA chain `d = fma(a7, b7, ... fma(a0, b0, c))` bit for bit. This probe asks the
// same questions of the fp16 tensor op documented for OUR card:
//
//   WMMA  m16n16k16 row.col f16 x f16 -> f32 accumulate   (sm_70+; the .f32-acc
//          plain-mma.m16n8k8 form is an sm_80 instruction — see the negative result
//          below — so wmma.sync is the fp32-accumulate tensor path on Turing).
//
// Tests:
//   A1  wmma row vs ascending-K scalar FMA chain (__fmaf_rn, same init c) — bitwise?
//   A2  row-batch invariance: a row's bits with re-randomized neighbor rows
//   A3  slot invariance: the same row planted at tile rows 0 and 9
//   A4  determinism: same inputs re-run — bitwise
//   B   dp4a integer dot — exactness sanity (trivially exact; the fork's PTQ1_0
//       IMMA path and llama.cpp MMQ inherit the same property: integer partial
//       sums associate, so they are order- and batch-invariant by construction)
//   C   measured peaks (2 s warmup total, then min..max of 5 reps — lab method):
//       WMMA TFLOPS, FFMA scalar TFLOPS, dp4a int-TOPS -> inputs for the lane
//       crossover table (section D).
//
// Negative result kept for the record (v1 of this probe, 2026-09-27):
//   mma.sync.aligned.m16n8k8.row.col.f32.f16.f16.f32 ptxas-accepts and RUNS on
//   sm_75 under CUDA 13.3, but a one-hot calibration (A[3][5]=1, B[5][2]=7, C=0)
//   yields D[3][2]=7.03906 instead of exactly 7, plus structured garbage in every
//   other output (~(2n+1)*2^-23 in row 3, tiny values in rows 8..15 whose A inputs
//   were all zeros). The accumulator does not honor the documented f32 semantics
//   on this chip: treat the plain-mma f32-accumulate forms as sm_80-only, and use
//   wmma.sync (this file) or f16-accumulate mma.sync on sm_75. The load-bearing
//   property for lane decode is A2+A3+A4 anyway — see simd_qmm.py's mma_one_row
//   fallback: if A1 fails, serial decoding routes through the MMA kernel too.
//
// Build:  nvcc -O3 -std=c++17 -arch=sm_75 -o /tmp/probe_sm75 notes/mma_bitslice_probe_sm75.cu
// No --use_fast_math anywhere — exactness is the subject. __fmaf_rn is explicit.
//
// The lane semantics of wmma.sync: one warp = one 16x16 output tile; A is the
// activation row block (16 rows of K), B the weights (K x 16 column block,
// stored row-major = wmma matrix_b row_major, ldm 16), reduce over K in ascending
// 16-element tiles. B padded to 16 columns with zeros.

#include <cstdio>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <utility>
#include <random>
#include <cuda_fp16.h>
#include <mma.h>

#define CHECK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { \
  fprintf(stderr, "CUDA error %s at line %d\n", cudaGetErrorString(e_), __LINE__); exit(1); } } while (0)

using namespace nvcuda::wmma;

// ---------- A: WMMA m16n16k16 f16xf16->f32, K tiles of 16, ascending order ----------
__global__ void wmma_m16n16k16(const half* __restrict__ A, const half* __restrict__ B,
                                const float* __restrict__ C, float* __restrict__ D, int K) {
  const int warpid = (blockIdx.x * blockDim.x + threadIdx.x) >> 5;
  const int m0 = warpid * 16;                 // this warp's 16 A rows (single tile: m0=0)
  fragment<matrix_a, 16, 16, 16, half, row_major> fa;
  fragment<matrix_b, 16, 16, 16, half, row_major> fb;
  fragment<accumulator, 16, 16, 16, float> fc;
  // init accumulator from C (16x16 tile, row-major)
  load_matrix_sync(fc, C + (size_t)m0 * 16, 16, mem_row_major);
  for (int k0 = 0; k0 < K; k0 += 16) {
    load_matrix_sync(fa, A + (size_t)m0 * K + k0, K);
    load_matrix_sync(fb, B + (size_t)k0 * 16, 16);
    mma_sync(fc, fa, fb, fc);
  }
  store_matrix_sync(D + (size_t)m0 * 16, fc, 16, mem_row_major);
}

// Reference: ascending-K scalar FMA chain, one thread per (m,n), fp32 accumulate.
__global__ void scalar_chain(const half* __restrict__ A, const half* __restrict__ B,
                             const float* __restrict__ C, float* __restrict__ D, int K) {
  const int idx = blockIdx.x * blockDim.x + threadIdx.x;
  if (idx >= 256) return;
  const int m = idx >> 4, n = idx & 15;
  const half* Arow = A + (size_t)m * K;
  float acc = C[idx];
  for (int k = 0; k < K; ++k)
    acc = __fmaf_rn((float)Arow[k], (float)B[(size_t)k * 16 + n], acc);
  D[idx] = acc;
}

// ---------- B: dp4a integer exactness sanity ----------
__global__ void dp4a_test(const int* __restrict__ a, const int* __restrict__ b,
                          int* __restrict__ out, int n) {
  const int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i >= n) return;
  int r = 0;
  asm volatile("dp4a.s32.s32 %0, %1, %2, %3;\n" : "=r"(r) : "r"(a[i]), "r"(b[i]), "r"(0));
  out[i] = r;
}

// ---------- C: peak kernels (compute-roofline inputs for the lane crossover) ----------
__global__ void wmma_peak(float* sink, int iters) {
  fragment<matrix_a, 16, 16, 16, half, row_major> fa;
  fragment<matrix_b, 16, 16, 16, half, row_major> fb;
  fragment<accumulator, 16, 16, 16, float> fc[4];   // 4 independent chains: ILP 4
  fill_fragment(fa, __float2half(1.0f));
  fill_fragment(fb, __float2half(0.5f));
  #pragma unroll
  for (int j = 0; j < 4; ++j) fill_fragment(fc[j], 0.0f);
  for (int i = 0; i < iters; ++i) {
    #pragma unroll
    for (int j = 0; j < 4; ++j) mma_sync(fc[j], fa, fb, fc[j]);
  }
  float s = 0.f;
  #pragma unroll
  for (int j = 0; j < 4; ++j) s += fc[j].x[0];
  if (s == -1.0f) *sink = s;   // never true
}

__global__ void ffma_peak(float* sink, int iters) {
  float c[16];
  #pragma unroll
  for (int i = 0; i < 16; ++i) c[i] = threadIdx.x * 1e-6f + i * 0.01f;
  const float a = 1.0000001f, b = 1e-7f;
  for (int i = 0; i < iters; ++i) {
    #pragma unroll
    for (int j = 0; j < 16; ++j) c[j] = __fmaf_rn(a, b, c[j]);
  }
  float s = 0.f;
  #pragma unroll
  for (int j = 0; j < 16; ++j) s += c[j];
  if (s == -1.0f) *sink = s;               // never true
}

__global__ void dp4a_peak(int* sink, int iters) {
  int c[16];
  #pragma unroll
  for (int i = 0; i < 16; ++i) c[i] = threadIdx.x + i;
  const int a = 0x05050505, b = 0x03030303;
  for (int i = 0; i < iters; ++i) {
    #pragma unroll
    for (int j = 0; j < 16; ++j)
      asm volatile("dp4a.s32.s32 %0, %1, %2, %0;\n" : "+r"(c[j]) : "r"(a), "r"(b));
  }
  int s = 0;
  #pragma unroll
  for (int j = 0; j < 16; ++j) s += c[j];
  if (s == -1) *sink = s;                   // never true
}

// ---------- harness ----------
// A5: column-slot invariance — the same B-column data at columns 0 and 9.
// A lane kernel can place batch rows on the M axis (row slots, LIKE TensorFold) or the
// N axis (column slots, weights transposed onto M). A5 vs A3 decides which axis is legal.
// A6: duplicate-slots mirror — all 16 A rows carry the same data: does D[k] == D[0]?
// If yes, serial decode can be defined as a 16-duplicate pass and slot-dependence dies.
static int64_t bitdiff(const float* a, const float* b, int n, double* maxreldiff) {
  int64_t bad = 0; double worst = 0.0;
  for (int i = 0; i < n; ++i) {
    uint32_t x, y; memcpy(&x, &a[i], 4); memcpy(&y, &b[i], 4);
    if (x != y) {
      ++bad;
      double denom = b[i] < 0 ? -(double)b[i] : (double)b[i];
      double rel = denom > 1e-30 ? ((double)a[i] - (double)b[i]) / denom : 1.0;
      if (rel < 0) rel = -rel;
      if (rel > worst) worst = rel;
    }
  }
  *maxreldiff = worst;
  return bad;
}

int main() {
  cudaDeviceProp prop; CHECK(cudaGetDeviceProperties(&prop, 0));
  printf("device: %s  SMs=%d  cc=%d.%d\n",
         prop.name, prop.multiProcessorCount, prop.major, prop.minor);

  std::mt19937_64 rng(20260927ULL);
  std::uniform_real_distribution<float> af(-4.0f, 4.0f), bf(-4.0f, 4.0f), cf(-8.0f, 8.0f);

  const int Ks[] = {64, 512, 5120};
  const int TRIALS[] = {512, 512, 256};
  int64_t col_bad_tot = 0, dup_bad_tot = 0;

  half *dA, *dB, *hA, *hB;
  float *dC, *dD1, *dD2, *hC;
  CHECK(cudaMalloc(&dA, 16 * 5120 * sizeof(half)));
  CHECK(cudaMalloc(&dB, 5120 * 16 * sizeof(half)));
  CHECK(cudaMalloc(&dC, 256 * sizeof(float)));
  CHECK(cudaMalloc(&dD1, 256 * sizeof(float)));
  CHECK(cudaMalloc(&dD2, 256 * sizeof(float)));
  hA = (half*)malloc(16 * 5120 * sizeof(half));
  hB = (half*)malloc(5120 * 16 * sizeof(half));
  hC = (float*)malloc(256 * sizeof(float));
  half* saved0 = (half*)malloc(5120 * sizeof(half));

  printf("\n== A: WMMA m16n16k16 (f16 in, f32 acc): TensorFold bit-stability questions ==\n");
  printf("%6s %6s | %9s | %10s | %11s | %11s | %8s\n",
         "K", "trials", "chain-eq", "maxreldiff", "row-invar", "slot-invar", "repeat");
  for (int ik = 0; ik < 3; ++ik) {
    const int K = Ks[ik], T = TRIALS[ik];
    int64_t chain_eq = 0, chain_bad = 0, row_bad = 0, slot_bad = 0, det_bad = 0;
    double worst_rel = 0.0;
    for (int trial = 0; trial < T; ++trial) {
      for (int i = 0; i < 16 * K; ++i) hA[i] = __float2half(af(rng));
      for (int i = 0; i < K * 16; ++i) hB[i] = __float2half(bf(rng));
      for (int i = 0; i < 256; ++i) hC[i] = cf(rng);
      CHECK(cudaMemcpy(dA, hA, 16 * K * sizeof(half), cudaMemcpyHostToDevice));
      CHECK(cudaMemcpy(dB, hB, K * 16 * sizeof(half), cudaMemcpyHostToDevice));
      CHECK(cudaMemcpy(dC, hC, 256 * sizeof(float), cudaMemcpyHostToDevice));

      wmma_m16n16k16<<<1, 32>>>(dA, dB, dC, dD1, K);   // baseline run
      wmma_m16n16k16<<<1, 32>>>(dA, dB, dC, dD2, K);   // A4: determinism repeat
      CHECK(cudaDeviceSynchronize());
      float hbase[256], hrep[256], href[256];
      CHECK(cudaMemcpy(hbase, dD1, 1024, cudaMemcpyDeviceToHost));
      CHECK(cudaMemcpy(hrep, dD2, 1024, cudaMemcpyDeviceToHost));
      double mrd;
      det_bad += bitdiff(hrep, hbase, 256, &mrd);

      // A1: scalar chain reference into dD2
      scalar_chain<<<1, 256>>>(dA, dB, dC, dD2, K);
      CHECK(cudaDeviceSynchronize());
      CHECK(cudaMemcpy(href, dD2, 1024, cudaMemcpyDeviceToHost));
      int64_t bad = bitdiff(hbase, href, 256, &mrd);
      chain_bad += bad; chain_eq += 256 - bad;
      if (mrd > worst_rel) worst_rel = mrd;

      // A2: row-batch invariance — row 0 unchanged, rows 1..15 re-randomized
      memcpy(saved0, hA, K * sizeof(half));
      for (int i = K; i < 16 * K; ++i) hA[i] = __float2half(af(rng));
      memcpy(hA, saved0, K * sizeof(half));
      CHECK(cudaMemcpy(dA, hA, 16 * K * sizeof(half), cudaMemcpyHostToDevice));
      wmma_m16n16k16<<<1, 32>>>(dA, dB, dC, dD2, K);
      CHECK(cudaDeviceSynchronize());
      float hrow[256]; CHECK(cudaMemcpy(hrow, dD2, 1024, cudaMemcpyDeviceToHost));
      row_bad += bitdiff(hrow, hbase, 16, &mrd);   // row 0's 16 outputs only

      // A3: slot invariance — row 0's data planted at tile row 9
      memcpy(hA + 9 * K, saved0, K * sizeof(half));
      CHECK(cudaMemcpy(dA, hA, 16 * K * sizeof(half), cudaMemcpyHostToDevice));
      wmma_m16n16k16<<<1, 32>>>(dA, dB, dC, dD2, K);
      CHECK(cudaDeviceSynchronize());
      float hslot[256]; CHECK(cudaMemcpy(hslot, dD2, 1024, cudaMemcpyDeviceToHost));
      slot_bad += bitdiff(hslot + 9 * 16, hbase, 16, &mrd);   // row 9's outputs vs baseline row 0

      // A5: column-slot invariance — B col 0's data planted at col 9, A fresh
      for (int i = 0; i < 16 * K; ++i) hA[i] = __float2half(af(rng));
      for (int i = 0; i < K * 16; ++i) hB[i] = __float2half(bf(rng));   // fresh B
      float savedb[5120];
      for (int k = 0; k < K; ++k) savedb[k] = (float)hB[(size_t)k * 16 + 0];
      for (int k = 0; k < K; ++k) hB[(size_t)k * 16 + 9] = __float2half(savedb[k]);
      CHECK(cudaMemcpy(dA, hA, 16 * K * sizeof(half), cudaMemcpyHostToDevice));
      CHECK(cudaMemcpy(dB, hB, K * 16 * sizeof(half), cudaMemcpyHostToDevice));
      wmma_m16n16k16<<<1, 32>>>(dA, dB, dC, dD2, K);
      CHECK(cudaDeviceSynchronize());
      float hcol[256]; CHECK(cudaMemcpy(hcol, dD2, 1024, cudaMemcpyDeviceToHost));
      // D[m][0] must equal D[m][9] bitwise, all 16 rows
      for (int m = 0; m < 16; ++m) {
        double mr5;
        col_bad_tot += bitdiff(hcol + m * 16 + 9, hcol + m * 16, 1, &mr5);
      }

      // A6: duplicate-slots mirror — all 16 A rows the same; D[k] vs D[0] bitwise
      for (int k = 0; k < K; ++k) {
        half v = hA[k];
        for (int m = 0; m < 16; ++m) hA[(size_t)m * K + k] = v;
      }
      CHECK(cudaMemcpy(dA, hA, 16 * K * sizeof(half), cudaMemcpyHostToDevice));
      wmma_m16n16k16<<<1, 32>>>(dA, dB, dC, dD2, K);
      CHECK(cudaDeviceSynchronize());
      float hdup[256]; CHECK(cudaMemcpy(hdup, dD2, 1024, cudaMemcpyDeviceToHost));
      for (int m = 0; m < 16; ++m) {
        double mr6;
        dup_bad_tot += bitdiff(hdup + m * 16, hdup, 16, &mr6);   // row m's outputs vs row 0's
      }
    }
    printf("%6d %6d | %6.2f%% | %10.3g | %7.3f%% ok | %7.3f%% ok | %7lld\n",
           K, T, 100.0 * chain_eq / (chain_eq + chain_bad), worst_rel,
           100.0 * (1.0 - (double)row_bad / (T * 16.0)),
           100.0 * (1.0 - (double)slot_bad / (T * 16.0)), (long long)det_bad);
    printf("   A5 col-slot invariance (col 0 vs col 9, 16 rows): %lld / %d mismatches\n",
           (long long)col_bad_tot, T * 16);
    printf("   A6 duplicate-slots mirror     (row m vs row 0): %lld / %d mismatches\n",
           (long long)dup_bad_tot, T * 256);
    col_bad_tot = 0; dup_bad_tot = 0;
  }

  // ---------- B: dp4a ----------
  {
    const int N = 1 << 20;
    int *ha = (int*)malloc(N * 4), *hb = (int*)malloc(N * 4), *ho = (int*)malloc(N * 4);
    int *da, *db, *dou;
    CHECK(cudaMalloc(&da, N * 4)); CHECK(cudaMalloc(&db, N * 4)); CHECK(cudaMalloc(&dou, N * 4));
    for (int i = 0; i < N; ++i) { ha[i] = (int)rng(); hb[i] = (int)rng(); }
    CHECK(cudaMemcpy(da, ha, N * 4, cudaMemcpyHostToDevice));
    CHECK(cudaMemcpy(db, hb, N * 4, cudaMemcpyHostToDevice));
    dp4a_test<<<(N + 255) / 256, 256>>>(da, db, dou, N);
    CHECK(cudaDeviceSynchronize());
    CHECK(cudaMemcpy(ho, dou, N * 4, cudaMemcpyDeviceToHost));
    int64_t bad = 0;
    for (int i = 0; i < N; ++i) {
      int8_t pa[4], pb[4];
      memcpy(pa, &ha[i], 4); memcpy(pb, &hb[i], 4);
      int ref = (int)pa[0] * pb[0] + (int)pa[1] * pb[1] + (int)pa[2] * pb[2] + (int)pa[3] * pb[3];
      if (ref != ho[i]) ++bad;
    }
    printf("\n== B: dp4a.s32 integer dot vs host scalar: %lld / %d mismatches ==\n",
           (long long)bad, N);
    free(ha); free(hb); free(ho); cudaFree(da); cudaFree(db); cudaFree(dou);
  }

  // ---------- C: peaks (1 s warmup, then min..max of 5 reps) ----------
  printf("\n== C: measured peaks on this card (after warmup; min..max of 5 reps) ==\n");
  float* fsink; CHECK(cudaMalloc(&fsink, 4));
  int* isink;   CHECK(cudaMalloc(&isink, 4));
  const int REPS = 5;
  double flops_wmma[REPS], flops_ffma[REPS], tops_dp4a[REPS];
  cudaEvent_t es, ee; CHECK(cudaEventCreate(&es)); CHECK(cudaEventCreate(&ee));
  const int SM = prop.multiProcessorCount;

  { // WMMA: m16n16k16 = 4096 MACs = 8192 FLOPs per mma; 8 warps/block; 2*SM blocks
    const int iters = 300000;
    wmma_peak<<<2 * SM, 256>>>(fsink, 500000);        // warmup (clocks ramp)
    CHECK(cudaDeviceSynchronize());
    for (int r = 0; r < REPS; ++r) {
      CHECK(cudaEventRecord(es));
      wmma_peak<<<2 * SM, 256>>>(fsink, iters);
      CHECK(cudaEventRecord(ee));
      CHECK(cudaEventSynchronize(ee));
      float ms; CHECK(cudaEventElapsedTime(&ms, es, ee));
      flops_wmma[r] = (double)2 * SM * 8 * iters * 4 * 8192.0 / (ms * 1e-3) / 1e12;
    }
  }
  { // FFMA: 16 independent chains per thread
    const int iters = 300000;
    ffma_peak<<<2 * SM, 256>>>(fsink, 500000);
    CHECK(cudaDeviceSynchronize());
    for (int r = 0; r < REPS; ++r) {
      CHECK(cudaEventRecord(es));
      ffma_peak<<<2 * SM, 256>>>(fsink, iters);
      CHECK(cudaEventRecord(ee));
      CHECK(cudaEventSynchronize(ee));
      float ms; CHECK(cudaEventElapsedTime(&ms, es, ee));
      flops_ffma[r] = (double)2 * SM * 256 * iters * 16 / (ms * 1e-3) / 1e12;
    }
  }
  { // dp4a: 8 int8 MACs per instruction, 16 instructions per thread per iter
    const int iters = 300000;
    dp4a_peak<<<2 * SM, 256>>>(isink, 500000);
    CHECK(cudaDeviceSynchronize());
    for (int r = 0; r < REPS; ++r) {
      CHECK(cudaEventRecord(es));
      dp4a_peak<<<2 * SM, 256>>>(isink, iters);
      CHECK(cudaEventRecord(ee));
      CHECK(cudaEventSynchronize(ee));
      float ms; CHECK(cudaEventElapsedTime(&ms, es, ee));
      tops_dp4a[r] = (double)2 * SM * 256 * iters * 16 * 8 / (ms * 1e-3) / 1e12;  // int8 MACs/s
    }
  }
  auto rng_of = [](const double* v, int n) {
    double lo = v[0], hi = v[0];
    for (int i = 1; i < n; ++i) { if (v[i] < lo) lo = v[i]; if (v[i] > hi) hi = v[i]; }
    return std::make_pair(lo, hi);
  };
  auto w = rng_of(flops_wmma, REPS);
  auto f = rng_of(flops_ffma, REPS);
  auto d = rng_of(tops_dp4a, REPS);
  printf("WMMA m16n16k16 f16xf16->fp32 : %6.2f .. %6.2f TFLOPS\n", w.first, w.second);
  printf("scalar FFMA fp32             : %6.2f .. %6.2f TFLOPS\n", f.first, f.second);
  printf("dp4a int8 dot                : %6.2f .. %6.2f int-TOPS (MACs)\n", d.first, d.second);
  printf("sanity vs spec: 2080 fp32 FMA spec ~10.1 TF at boost, fp16 tensor ~20-26 TF\n");

  // ---------- D: lane crossover table (uses the lab's measured 425-427 GB/s bus) ----------
  {
    const double BW = 425e9;                 // measured 2026-09-25 (roofline_probe_sm75.cu)
    const double N = 17408.0, K = 5120.0;
    const double Wbytes = N * K / 2.0;      // 4-bit affine (q4_0 class)
    const double Tmem = Wbytes / BW;
    const double TF = (w.first + w.second) / 2.0;
    const double Trow = 2.0 * N * K / (TF * 1e12);
    printf("\n== D: lane crossover for a 17408x5120 4-bit layer (measured peaks, BW=425 GB/s) ==\n");
    printf("T_mem(one pass, all rows) = %.1f us, T_compute/row = %.2f us -> rows_free ~= %.1f\n",
           Tmem * 1e6, Trow * 1e6, Tmem / Trow);
    printf("%5s %12s %12s\n", "rows", "pass(us)", "speedup(x)");
    int Rs[] = {1, 2, 4, 8, 16, 32};
    for (int r : Rs) {
      double t = Tmem > r * Trow ? Tmem : r * Trow;
      printf("%5d %12.1f %12.2f\n", r, t * 1e6, r * Tmem / t);
    }
  }

  free(hA); free(hB); free(hC); free(saved0);
  cudaFree(dA); cudaFree(dB); cudaFree(dC); cudaFree(dD1); cudaFree(dD2);
  printf("\nprobe complete\n");
  return 0;
}