# Why RAG needs a merge gate that remembers

[Back to the README](../README.md)

Most RAG changes ship like untested code: someone tweaks a chunk size, swaps an embedding model or edits a prompt, tries a few questions by hand, and merges. Nothing fails loudly when quality slips. The retriever quietly stops returning the right chunk for some questions, and the problem surfaces weeks later. `rag-eval-gate` is a small tool that turns "did this change make the RAG app worse?" into a build result. This note explains the design choices and where they stop being enough.

## Why fixed thresholds are the wrong gate

The obvious approach is a fixed bar: fail the build if context recall is below 0.8. That breaks in two ways. First, absolute scores depend on the dataset, the number of chunks retrieved and the metric. In the bundled sample, `context_precision` is 0.333 for a perfectly healthy run, because the run retrieves three chunks and each question has one gold chunk. Second, a fixed bar only tells you about the absolute level. It cannot say "this pull request made things worse", which is the only question a merge gate needs to answer.

So the gate compares against a baseline instead. You score a known-good run, promote it with `reg baseline promote`, and commit the resulting `baseline.json`. From then on, every pull request is judged against that file. The baseline stores per-question scores, not only means, and it carries a SHA-256 fingerprint of the dataset. If anyone edits a question or a gold answer, the comparison refuses to run until a new baseline is promoted, so you cannot silently compare scores from two different tests.

## Margins and floors

Each metric in `gate.yaml` gets its own allowed drop, either absolute (`max_drop`) or relative (`max_drop_rel`), and a severity of `error` or `warn`. Different metrics deserve different tolerances: the sample config allows 0.05 on recall and precision, a tighter 0.03 on NDCG, and a 10% relative drop on `rouge_l_recall` as a warning only. A metric can also carry a hard `min` floor, which is never softened. In the bundled regressed run, faithfulness falls from 1.000 to 0.567 and is reported as `BELOW FLOOR` against a floor of 0.70, whatever the noise test thinks.

## Noise: don't block on a few unlucky questions

With a few dozen questions, a mean can move by more than a margin for no real reason. The gate therefore applies a second condition. A metric fails only if the mean drop exceeds its margin and the paired-bootstrap confidence interval of the drop excludes zero. Paired means each question is compared with itself across the baseline and the current run, and the bootstrap resamples those per-question deltas with a fixed seed (2000 samples at 95% in the sample config), so the same inputs always produce the same verdict. In the healthy sample run, NDCG falls from 1.000 to 0.963, which is past its 0.03 margin, but the interval reaches zero, so the report says `pass (drop within noise)` instead of blocking the merge.

The report also lists the individual questions that got worse, whether or not the metric failed. That matters because the noise test has a known blind spot, which LIMITATIONS.md states plainly: a real regression that touches only a few items can be called noise. The per-question list is the safety net, since a reviewer can see exactly which questions moved. The gate also refuses to run on fewer than `min_items` questions (20 by default) and exits with code 2 rather than produce a confident-looking answer from a tiny sample.

## Offline, deterministic metrics

All twelve metrics in v0.1 come from continuous-eval's deterministic classes: chunk precision, recall and F1, ranking metrics (MAP, MRR, NDCG), and token-overlap, ROUGE and BLEU measures of faithfulness and correctness. There is no model call and no API key. That is a deliberate trade for a first version. A gate that runs in CI on every pull request has to be cheap, repeatable and runnable from a fresh clone, and a model-graded metric is none of those by default. The cost is honest and documented. These metrics are lexical, so they catch retrieval loss (the right chunk is no longer returned) and off-context answers, but they miss a paraphrased hallucination, such as an answer that reuses the context's words while changing a number or negating a claim. Treat the gate as a tripwire for the cheap, common regressions, not as proof the answers are correct.

continuous-eval is pinned at an exact version, used unmodified and credited in NOTICE. This repository adds what it lacks: baseline files, per-metric margins, the paired bootstrap, ID coverage checks, reports and the CI integration.

## Using it

The CLI has a small surface: `reg score`, `reg baseline promote`, `reg compare`, `reg gate`, `reg list-metrics` and `reg setup`. In a pull request you produce `run.jsonl` from your app (the retrieved chunks and the answer for each question ID), then run `reg gate` with the dataset, run, baseline and gate config. Exit code 0 means pass, 1 means a gated metric regressed, and 2 means the inputs were wrong, for example mismatched IDs or a dataset that does not match the baseline. The report can be console, Markdown or JSON.

The same gate ships as a composite GitHub Action. It installs the package, runs the gate, writes the Markdown report to the job summary, optionally updates a sticky pull-request comment, and fails the job on a regression. Inputs reach the shell through environment variables rather than string interpolation. The repository's own CI dogfoods it: the healthy sample run must pass, and the regressed one must fail.

## Limitations

- **Python 3.10 to 3.12 only.** continuous-eval 0.3.14.post2 declares `requires-python <3.13`, so this project inherits the cap.
- **A one-time `reg setup` step.** continuous-eval downloads NLTK data when its retrieval module is imported. Run `reg setup` once, or point `NLTK_DATA` at a prepared folder for air-gapped use. After that, scoring is offline.
- **Lexical metrics** and the **noise blind spot** described above.
- **A known advisory** in a transitive dependency, json-repair. SECURITY.md explains why v0.1 never reaches the affected code, and CI ignores that single advisory by ID.
- **Scope.** It covers RAG question answering only, and it keeps no history. Each run compares two files, so keeping baselines in git is the history.

## What is next

The first addition is opt-in model-graded metrics, behind an extra so the default install stays key-free, to cover the paraphrased-hallucination gap. The second is fitting this gate into a longer chain. [corpusgate](https://github.com/rvspraveen/corpusgate) checks the corpus before it is ingested, and this gate checks answer quality after retrieval and generation. A governed RAG project, planned and not yet published, would add access control and a leak check on top. Together they would cover data in, answers out, and who is allowed to see what.
