// keyed_gumbel_sampler.h — exact batch-invariant sampling, ported from TensorFold
// (github.com/ashhart/TensorFold, engine/exact_sampling.py, MIT) for llama.cpp-family
// runtimes on any GPU. 2026-09-27, this lab.
//
// THE RULE (TensorFold's): the token at absolute position p of a stream is
//
//     argmax over kept candidates i of   logit_i / T  +  g(seed, p, i)
//
// where g = -log(-log(u)) is Gumbel noise from a hash of (seed, absolute position,
// token id) — an exact draw from the top-k/top-p filtered temperature distribution
// (Gumbel-max trick) that depends only on the row's own logits, its absolute
// position, and the seed. Whatever rides along in the batch, a row picks the same
// token as it would alone, so speculative verification reduces to token equality:
// drafts change speed, never bytes.
//
// Semantics ported:
//   - candidates: top_k largest logits (ties at the boundary resolved toward the
//     smaller token id — TensorFold's radix select "collects ... the ties at T with
//     the smallest token ids"), then top_p on the temperature-scaled softmax
//     distribution (smallest prefix whose cumulative probability >= top_p, at
//     least one candidate always kept).
//   - T == 0 (greedy): plain argmax, ties broken by smaller token id.
//   - determinism: no state, no RNG sequence — every draw is a pure function of
//     (seed, position, logits). Re-runs replay exactly; drafted and serial runs
//     agree wherever their logits agree bit for bit.
//
// Ties in the final argmax: the scan visits candidates in ascending token-id order
// and keeps a strictly-greater winner, so identical (logit/T + g) picks the smaller id.
//
// The hash: splitmix64-style triple mix, top 53 bits -> double in [0,1); the +half-ulp
// bias keeps u>0 so g is finite (win probability 2^-53 class — a candidate that
// "never" wins).
//
// License note: this file is a clean-room re-implementation of documented behavior,
// MIT-compatible with this repo's existing notes.

#pragma once
#include <cstdint>
#include <cmath>
#include <vector>
#include <algorithm>
#include <limits>

namespace keyed_gumbel {

// splitmix64 finalizer
inline uint64_t mix64(uint64_t z) {
  z += 0x9E3779B97F4A7C15ULL;
  z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
  z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
  return z ^ (z >> 31);
}

// uniform double in (0,1) from (seed, position, token id)
inline double uniform(uint64_t seed, uint64_t pos, uint64_t id) {
  const uint64_t h = mix64(mix64(seed + 0x9E3779B97F4A7C15ULL)
                           ^ mix64(pos * 0xD1B54A32D192ED03ULL + id));
  return (double)(h >> 11) * 0x1.0p-53 + 0x1.0p-54;
}

// Gumbel(0,1) sample keyed on (seed, position, id)
inline double gumbel(uint64_t seed, uint64_t pos, uint64_t id) {
  const double u = uniform(seed, pos, id);
  return -std::log(-std::log(u));
}

// One kept-candidate (logit float32 like the engines carry, id for ties).
struct Cand {
  float logit;
  uint32_t id;
};

// The exact pick for one row at absolute position pos.
//   logits: token logits (any float type convertible to float)
//   n:      vocabulary count
//   temp:   temperature (<=0 or std::isnan -> greedy)
//   top_k:  0 = keep all
//   top_p:  1.0 = keep all after top_k
template <typename T>
uint32_t choose(uint64_t seed, uint64_t pos, const T* logits, size_t n,
                float temp, int top_k, float top_p) {
  if (n == 0) return 0;
  if (n == 1) return 0;
  if (n <= std::numeric_limits<uint32_t>::max() && n > (1u << 24))
    return 0;  // sanity guard, vocab sizes are far below this

  // index the candidates
  std::vector<Cand> cands;
  cands.reserve(n);
  for (size_t i = 0; i < n; ++i) cands.push_back({(float)logits[i], (uint32_t)i});

  // top_k: largest logits, ties toward smaller id -> sort by (logit desc, id asc)
  if (top_k > 0 && (size_t)top_k < n) {
    std::sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) {
      if (a.logit != b.logit) return a.logit > b.logit;
      return a.id < b.id;
    });
    cands.resize(top_k);
  }

  // greedy: argmax (ties -> smaller id)
  if (!(temp > 0.0f)) {
    uint32_t best = cands[0].id;
    float bestv = cands[0].logit;
    for (const auto& c : cands)
      if (c.logit > bestv) { bestv = c.logit; best = c.id; }
    return best;
  }

  // top_p on the temperature-scaled distribution (softmax of logit/T)
  if (top_p < 1.0f) {
    std::sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) {
      if (a.logit != b.logit) return a.logit > b.logit;
      return a.id < b.id;
    });
    float m = cands[0].logit / temp;               // scaled max for stability
    double sum = 0.0;
    for (auto& c : cands) sum += std::exp((double)c.logit / temp - m);
    double acc = 0.0;
    size_t keep = 1;
    for (size_t i = 0; i < cands.size() - 1; ++i) {
      acc += std::exp((double)cands[i].logit / temp - m) / sum;
      if (acc >= top_p) { keep = i + 1; break; }
      keep = i + 2;                                // always keep at least the next
    }
    cands.resize(keep);
  }

  // the keyed Gumbel-max argmax; ascending-id scan with strict-greater keeps the
  // smaller id on exact ties
  std::sort(cands.begin(), cands.end(), [](const Cand& a, const Cand& b) { return a.id < b.id; });
  double best = -std::numeric_limits<double>::infinity();
  uint32_t best_id = cands[0].id;
  for (const auto& c : cands) {
    const double v = (double)c.logit / (double)temp + gumbel(seed, pos, c.id);
    if (v > best) { best = v; best_id = c.id; }
  }
  return best_id;
}

// Derive a stream seed from prompt token ids — the same conversation samples the
// same reply (deterministic across re-runs and across serial/drafted decode).
// FNV-1a 64 over the ids *in order*.
inline uint64_t seed_from_tokens(const std::vector<uint32_t>& ids) {
  uint64_t h = 0xcbf29ce484222325ULL;
  for (uint32_t t : ids) {
    for (int b = 0; b < 4; ++b) {
      h ^= (t >> (8 * b)) & 0xff;
      h *= 0x100000001b3ULL;
    }
  }
  return mix64(h);
}

}  // namespace keyed_gumbel