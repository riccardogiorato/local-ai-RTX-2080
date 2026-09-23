# Registry cross-links

## qwen35-4b-q4km-mtp-rtx-2080-8gb-llamacpp-tp1

- Local recipe: [recipes/qwen35-4b-mtp-q4km-llamacpp.md](../recipes/qwen35-4b-mtp-q4km-llamacpp.md)
- Status in [0xsero/local-ai-registry](https://github.com/0xsero/local-ai-registry): **validated, `recommended: true`** for hardware `rtx-2080-8gb`
- Acceptance evidence: speed-sweep `qwen35-4b-…-acceptance` (decode 112.8 tok/s, TTFT 71 ms); raw JSONL in [evidence/](../evidence/) (v2 = final launch contract with batch flags)
- Contributed on branch `rtx-2080-recipes` on fork `riccardogiorato/local-ai-registry`; PR link added here once opened.

## qwen35-9b-q4km-mtp-rtx-2080-8gb-llamacpp-tp1

- Local recipe: [recipes/qwen35-9b-mtp-q4km-llamacpp.md](../recipes/qwen35-9b-mtp-q4km-llamacpp.md)
- Status in local-ai-registry: **validated**, plugin alternate for `rtx-2080-8gb`
- Acceptance evidence: speed-sweep `qwen35-9b-…-acceptance` (decode 76.4 tok/s, TTFT 102 ms)

## Upstream artifacts

- Hardware record `rtx-2080-8gb` (TU104, vendor-provenanced) — first Turing card in the registry
- Model-instance records pin the exact HF revisions listed in each local recipe; SHAs verified before any run here or in the registry.