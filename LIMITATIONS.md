# Limitations

rag-eval-gate v0.1 is a deliberately small, offline tool. Know these before you rely on it.

## The metrics are lexical

All v0.1 metrics are deterministic and come from continuous-eval: chunk matching with ROUGE-L, ranking metrics, and token-overlap, ROUGE and BLEU faithfulness and correctness.

- They catch **retrieval loss** (the right chunk is no longer returned) and **off-context answers** (the answer shares little wording with what was retrieved).
- They **miss paraphrased hallucinations**: an answer that reuses the context's words but changes a number or negates a claim can still score well.
- `context_precision` depends on how many chunks you retrieve. With top-3 and one gold chunk, the best possible score is 0.333.

LLM-judge metrics are planned for v0.2 behind an opt-in extra, so the default install stays key-free.

## The noise test has a blind spot for small, consistent drops

A metric fails only when its mean drop exceeds the margin **and** the paired-bootstrap confidence interval excludes zero. This stops one or two unlucky questions from blocking a merge, but it also means:

- A real regression that hits only a few items (for example 3 of 30) can be reported as `pass (drop within noise)`. Those items are still listed under "Items that got worse", so review them.
- Small eval sets give wide intervals. The gate refuses to run below `min_items` (default 20) and exits 2 instead of guessing.
- To be stricter, lower `bootstrap.confidence`, grow the dataset, or add a `min:` floor, which is never softened by the noise test.

## Upstream constraints

- **Python 3.10 to 3.12 only.** continuous-eval 0.3.14.post2 declares `requires-python <3.13`. Its last PyPI release was January 2025; a fix merged in August 2026 has not been released.
- **One-time network step.** continuous-eval downloads NLTK data when its retrieval module is imported. Run `reg setup` once (or set `NLTK_DATA` to a pre-populated folder for air-gapped use). After that, scoring is offline.
- **Install size** is about 260 MB (scikit-learn, NLTK and the OpenAI SDK come with continuous-eval even though v0.1 never calls a model).
- **Known advisory** in a transitive dependency, json-repair 0.31.0 (GHSA-xf7x-x43h-rpqh). See [SECURITY.md](SECURITY.md) for why it is not reachable.

## Scope

- RAG question-answering only. No SQL, tool-use or classification tasks yet, although continuous-eval has metrics for them.
- No history or dashboard: each run compares two files. Keep baselines in git to get history for free.
- The baseline is tied to the exact dataset by a SHA-256 fingerprint. Editing any question or gold answer requires re-scoring and promoting a new baseline, on purpose.
