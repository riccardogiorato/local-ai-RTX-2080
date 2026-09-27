// keyed_gumbel_sampler_test.cpp — validation harness for notes/keyed_gumbel_sampler.h
// Build:  g++ -O2 -std=c++17 -o /tmp/kg_test notes/keyed_gumbel_sampler_test.cpp && /tmp/kg_test
// All tests CPU-only; the point is that sampler-level exactness needs no GPU.
// Evidence numbers this harness prints are recorded in
// evidence/tensorfold-exactness-probe.jsonl.

#include "keyed_gumbel_sampler.h"
#include <cstdio>
#include <cmath>
#include <vector>
#include <random>

using keyed_gumbel::choose;
using keyed_gumbel::seed_from_tokens;

static int failures = 0;
#define CHECK_T(cond, name, detail) do { \
  if (cond) { printf("PASS %s\n", name); } \
  else { printf("FAIL %s — %s\n", name, detail); ++failures; } } while (0)

int main() {
  const uint64_t SEED = 0xC0FFEE1234567ULL;
  std::mt19937_64 rng(42);

  // ---- T1 determinism/purity: same (seed,pos,logits) -> same token, 50k samples ----
  {
    std::vector<float> logits(64);
    int bad = 0;
    for (int t = 0; t < 50000; ++t) {
      for (auto& l : logits) l = (float)((int)(rng() % 2001) - 1000) / 100.0f;
      uint64_t p = rng() % 1000;
      uint32_t a = choose(SEED, p, logits.data(), logits.size(), 0.7f, 0, 0.95f);
      uint32_t b = choose(SEED, p, logits.data(), logits.size(), 0.7f, 0, 0.95f);
      if (a != b) ++bad;
    }
    CHECK_T(bad == 0, "T1 determinism (50k re-draws identical)", "");
  }

  // ---- T2 batch invariance: neighbors never change a row's pick ----
  {
    const int R = 200, V = 64;
    std::vector<std::vector<float>> M(R, std::vector<float>(V));
    for (auto& row : M) for (auto& l : row) l = (float)((int)(rng() % 2001) - 1000) / 100.0f;
    std::vector<uint32_t> alone(R);
    for (int r = 0; r < R; ++r)
      alone[r] = choose(SEED, 1000 + r, M[r].data(), V, 0.8f, 40, 0.9f);
    // permute rows so every row rides with different neighbors; each row's pick is a
    // pure function of (seed, ITS position, ITS logits) and must not notice
    std::vector<std::vector<float>> M2;
    for (int r = 0; r < R; ++r) M2.push_back(M[(r * 7 + 13) % R]);
    int bad = 0;
    for (int r = 0; r < R; ++r) {
      int src = (r * 7 + 13) % R;   // row r of M2 is M[src]
      if (choose(SEED, 1000 + src, M2[r].data(), V, 0.8f, 40, 0.9f) != alone[src]) ++bad;
    }
    CHECK_T(bad == 0, "T2 batch invariance (200 rows, shuffled windows)", "");
  }

  // ---- T3 distribution: 3 tokens, temp 1 — Gumbel-max must match softmax ----
  {
    const int N = 300000, V = 3;
    float logits[V] = {2.0f, 0.5f, -1.0f};
    double s = std::exp(2.0) + std::exp(0.5) + std::exp(-1.0);
    double e0 = std::exp(2.0) / s, e1 = std::exp(0.5) / s, e2 = std::exp(-1.0) / s;
    long f[3] = {0, 0, 0};
    for (int p = 0; p < N; ++p) f[choose(SEED, p, logits, V, 1.0f, 0, 1.0f)]++;
    double g0 = (double)f[0] / N, g1 = (double)f[1] / N, g2 = (double)f[2] / N;
    printf("   T3 empirical %.4f/%.4f/%.4f vs softmax %.4f/%.4f/%.4f\n",
           g0, g1, g2, e0, e1, e2);
    CHECK_T(std::abs(g0 - e0) < 0.01 && std::abs(g1 - e1) < 0.01 && std::abs(g2 - e2) < 0.01,
            "T3 exact sampling distribution (300k draws, tol 0.01)", "");
  }

  // ---- T3b temperature: temp=100 → near-uniform over the 3 tokens ----
  {
    const int N = 300000, V = 3;
    float logits[V] = {2.0f, 0.5f, -1.0f};
    long f[3] = {0, 0, 0};
    for (int p = 0; p < N; ++p) f[choose(SEED, p, logits, V, 100.0f, 0, 1.0f)]++;
    printf("   T3b hot-temp empirical %.4f/%.4f/%.4f (expect ~0.333 each)\n",
           (double)f[0] / N, (double)f[1] / N, (double)f[2] / N);
    CHECK_T(std::abs((double)f[0] / N - 1.0 / 3) < 0.01
            && std::abs((double)f[1] / N - 1.0 / 3) < 0.01
            && std::abs((double)f[2] / N - 1.0 / 3) < 0.01,
            "T3b temperature flattening (tol 0.01)", "");
  }

  // ---- T4 top_k ----
  {
    float logits[5] = {1.0f, 5.0f, 0.0f, 3.0f, 2.0f};
    long f5 = 0, f3 = 0;
    for (int p = 0; p < 50000; ++p) {
      uint32_t t = choose(SEED, p, logits, 5, 1.0f, 1, 1.0f);
      if (t == 1) ++f5;  // argmax is id 1 (logit 5.0) — top_k=1 must always pick it
      t = choose(SEED, p, logits, 5, 1.0f, 2, 1.0f);
      if (t == 3) ++f3; // id 3 is 2nd largest; id 0 never
    }
    CHECK_T(f5 == 50000, "T4 top_k=1 always argmax", "");
    CHECK_T(f3 > 0 && f3 < 50000, "T4 top_k=2 samples within top-2 only", "");
  }

  // ---- T5 top_p on the scaled distribution ----
  {
    float logits[3] = {2.0f, 0.5f, -1.0f};   // p = (0.782, 0.174, 0.040)
    long f2 = 0;
    for (int p = 0; p < 100000; ++p)
      if (choose(SEED, p, logits, 3, 1.0f, 0, 0.90f) == 2) ++f2;
    CHECK_T(f2 == 0, "T5 top_p=0.90 excludes the 4% token", "");
    for (int p = 0; p < 100000; ++p)
      if (choose(SEED, p, logits, 3, 1.0f, 0, 0.99f) == 2) f2 = 1;
    CHECK_T(f2 == 1, "T5 top_p=0.99 includes the 4% token", "");
  }

  // ---- T5b min_p: threshold on the temperature-scaled distribution ----
  {
    // logits (0.4, 0.0, -6.0): p = (0.5993, 0.4007, 0.00015); min_p=0.05 drops token 2
    float lgs[3] = {0.4f, 0.0f, -6.0f};
    long appeared = 0;
    for (int p = 0; p < 100000; ++p)
      if (choose(SEED, p, lgs, 3, 1.0f, 0, 1.0f, 0.05f) == 2) ++appeared;
    CHECK_T(appeared == 0, "T5b min_p=0.05 excludes the 0.015% token", "");
    // min_p=0.0001 keeps it (p2 = 0.00015 >= 0.0001)
    appeared = 0;
    for (int p = 0; p < 100000; ++p)
      if (choose(SEED, p, lgs, 3, 1.0f, 0, 1.0f, 0.0001f) == 2) ++appeared;
    CHECK_T(appeared > 0 && appeared < 200,
            "T5b min_p=0.0001 keeps it at ~0.015% (15 expected in 100k)", "");
  }

  // ---- T6 greedy ties break by smaller id ----
  {
    float logits[4] = {1.0f, 1.0f, 1.0f, 1.0f};
    uint32_t t = choose(SEED, 7, logits, 4, 0.0f, 0, 1.0f);
    CHECK_T(t == 0, "T6 greedy tie -> smallest id", "");
    // tie at the top_k boundary: three equal 2.0 logits compete for one top_k slot;
    // the smaller id takes it, the other two never appear regardless of draw luck
    float lg[4] = {3.0f, 2.0f, 2.0f, 2.0f};
    t = choose(SEED, 7, lg, 4, 0.0f, 1, 1.0f);
    CHECK_T(t == 0, "T6 top-k boundary ties -> argmax anyway", "");
    bool losers_appeared = false;
    long wins1 = 0;
    for (int p = 0; p < 20000; ++p) {
      t = choose(SEED, p, lg, 4, 1.0f, 2, 1.0f);
      if (t == 2 || t == 3) losers_appeared = true;
      if (t == 1) ++wins1;
    }
    CHECK_T(!losers_appeared && wins1 > 1000,
            "T6 top_k=2 ties -> smaller id kept, losers excluded", "");
  }

  // ---- T7 position independence: adjacent draws uncorrelated ----
  {
    const int N = 100000;
    float logits[2] = {0.4f, 0.0f};   // p = (0.6, 0.4)
    long j00 = 0, j11 = 0;
    for (int i = 0; i < N; ++i) {
      uint32_t a = choose(SEED, 2 * i,     logits, 2, 1.0f, 0, 1.0f);
      uint32_t b = choose(SEED, 2 * i + 1, logits, 2, 1.0f, 0, 1.0f);
      if (a == 0 && b == 0) ++j00;
      if (a == 1 && b == 1) ++j11;
    }
    double e00 = 0.36, e11 = 0.16;
    printf("   T7 joint freqs %.4f/%.4f vs %.2f/%.2f (products)\n",
           (double)j00 / N, (double)j11 / N, e00, e11);
    CHECK_T(std::abs((double)j00 / N - e00) < 0.01 && std::abs((double)j11 / N - e11) < 0.01,
            "T7 position-keyed draws independent (tol 0.01)", "");
  }

  // ---- T8 seed derivation: order-sensitive, stable, mixing ----
  {
    std::vector<uint32_t> ids = {1, 2, 3, 42, 300, 65000};
    std::vector<uint32_t> rev(ids.rbegin(), ids.rend());
    CHECK_T(seed_from_tokens(ids) == seed_from_tokens(ids), "T8 seed_from_tokens stable", "");
    CHECK_T(seed_from_tokens(ids) != seed_from_tokens(rev), "T8 seed_from_tokens order-sensitive", "");
    CHECK_T(seed_from_tokens(ids) != seed_from_tokens({1, 2, 3, 42, 301, 65000}),
            "T8 seed_from_tokens input-sensitive", "");
  }

  printf(failures ? "\n%d FAILURES\n" : "\nALL TESTS PASS\n", failures);
  return failures ? 1 : 0;
}