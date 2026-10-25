// cuBLAS GEMM power burner for RTX 2080 (Turing, sm_75).
// Runs back-to-back GEMMs for the given number of seconds.
// Usage: burn <seconds> [f16|f32] [n]
//   f16: fp16 tensor-op GEMM (default) — compute-bound, high FLOP/W
//   f32: fp32 CUDA-core GEMM — the power-virus load on Turing
// Single C = A * B with alpha=1, beta=0; fp16 operands pinned to ~1.18
// (bits 0x3C3C) so partial sums stay finite at k=4096.
#include <cublas_v2.h>
#include <cuda_fp16.h>
#include <cuda_runtime.h>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#define CUDA_CHECK(x) do { cudaError_t e_ = (x); if (e_ != cudaSuccess) { \
  std::fprintf(stderr, "CUDA error %s at %s:%d\n", cudaGetErrorString(e_), __FILE__, __LINE__); std::exit(1); } } while (0)
#define CUBLAS_CHECK(x) do { cublasStatus_t s_ = (x); if (s_ != CUBLAS_STATUS_SUCCESS) { \
  std::fprintf(stderr, "cuBLAS error %d at %s:%d\n", (int)s_, __FILE__, __LINE__); std::exit(1); } } while (0)

int main(int argc, char** argv) {
  const int burn_seconds = argc > 1 ? std::atoi(argv[1]) : 480;
  const bool use_f32 = argc > 2 && std::strcmp(argv[2], "f32") == 0;
  const int n = argc > 3 ? std::atoi(argv[3]) : 4096;
  const double flops_per_gemm = 2.0 * n * n * n;

  cublasHandle_t handle;
  CUBLAS_CHECK(cublasCreate(&handle));

  auto t0 = std::chrono::steady_clock::now();
  long iters = 0;
  if (use_f32) {
    const size_t bytes = (size_t)n * n * sizeof(float);
    float *A = nullptr, *B = nullptr, *C = nullptr;
    CUDA_CHECK(cudaMalloc(&A, bytes));
    CUDA_CHECK(cudaMalloc(&B, bytes));
    CUDA_CHECK(cudaMalloc(&C, bytes));
    CUDA_CHECK(cudaMemset(A, 0x3C, bytes));  // float bits 0x3C3C3C3C is a tiny denormal-ish value: nonzero and safe to accumulate
    CUDA_CHECK(cudaMemset(B, 0x3C, bytes));
    CUDA_CHECK(cudaMemset(C, 0x00, bytes));
    float alpha = 1.0f, beta = 0.0f;
    for (;;) {
      double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
      if (elapsed >= burn_seconds) break;
      CUBLAS_CHECK(cublasGemmEx(handle, CUBLAS_OP_N, CUBLAS_OP_N, n, n, n,
                                &alpha, A, CUDA_R_32F, n,
                                B, CUDA_R_32F, n,
                                &beta, C, CUDA_R_32F, n,
                                CUBLAS_COMPUTE_32F, CUBLAS_GEMM_DEFAULT));
      CUDA_CHECK(cudaDeviceSynchronize());  // keep the launch queue from racing ahead of the GPU: wall time = burn time
      ++iters;
      if (iters % 50 == 0) {
        double now = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
        std::printf("t=%.1fs iters=%ld perf=%.2f GFLOP/s (f32 n=%d)\n", now, iters,
                    flops_per_gemm * iters / now / 1e9, n);
        std::fflush(stdout);
      }
    }
    cudaFree(A); cudaFree(B); cudaFree(C);
  } else {
    __half alpha = __float2half(1.0f);
    __half beta  = __float2half(0.0f);
    const size_t bytes = (size_t)n * n * sizeof(__half);
    __half *A = nullptr, *B = nullptr, *C = nullptr;
    CUDA_CHECK(cudaMalloc(&A, bytes));
    CUDA_CHECK(cudaMalloc(&B, bytes));
    CUDA_CHECK(cudaMalloc(&C, bytes));
    CUDA_CHECK(cudaMemset(A, 0x3C, bytes));
    CUDA_CHECK(cudaMemset(B, 0x3C, bytes));
    CUDA_CHECK(cudaMemset(C, 0x00, bytes));
    for (;;) {
      double elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
      if (elapsed >= burn_seconds) break;
      CUBLAS_CHECK(cublasGemmEx(handle, CUBLAS_OP_N, CUBLAS_OP_N, n, n, n,
                                &alpha, A, CUDA_R_16F, n,
                                B, CUDA_R_16F, n,
                                &beta, C, CUDA_R_16F, n,
                                CUBLAS_COMPUTE_16F, CUBLAS_GEMM_DEFAULT_TENSOR_OP));
    ++iters;
    if (iters % 200 == 0) {
      double now = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
      std::printf("t=%.1fs iters=%ld perf=%.2f TFLOP/s\n", now, iters,
                  flops_per_gemm * iters / now / 1e12);
      std::fflush(stdout);
    }
    }
  }
  double total = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
  std::printf("done: %ld gemms in %.1fs, avg %.2f TFLOP/s\n", iters, total,
              flops_per_gemm * iters / total / 1e12);
  return 0;
}
