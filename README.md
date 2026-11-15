# rag-eval-gate

**A merge gate for RAG quality.** It scores your RAG app's outputs, compares them with a saved baseline, and fails the build when a metric drops by more than you allow, but only when the drop is real rather than noise from a few questions.

**Write-up:** [Why RAG needs a merge gate that remembers](docs/writeup.md)

Built on [continuous-eval](https://github.com/relari-ai/continuous-eval) (Apache-2.0) as an unmodified dependency. Fully offline: no API key and no model download.

[![CI](https://github.com/rvspraveen/rag-eval-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/rvspraveen/rag-eval-gate/actions/workflows/ci.yml)
![Python 3.10 to 3.12](https://img.shields.io/badge/python-3.10%20%E2%80%93%203.12-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

## Run it

```bash
git clone https://github.com/rvspraveen/rag-eval-gate && cd rag-eval-gate
python3.12 -m venv .venv && . .venv/bin/activate
pip install .
reg setup     # one-time NLTK download used by continuous-eval
reg gate -d examples/dataset.jsonl -r examples/regressed_run.jsonl \
         -b examples/baseline.json -g examples/gate.yaml
```

The bundled regressed run loses the right chunk on 8 of 30 questions and drifts off-context on 5 more. Real output, exit code 1:

```text
rag-eval-gate FAIL: 4 failing of 5 metrics
30 items, paired bootstrap 2000 samples at 95%, baseline dataset 379945e1679b
 metric                     ┃ baseline ┃ current ┃  delta ┃ 95% CI           ┃ allowed          ┃ result
━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━
 context_recall             │    1.000 │   0.733 │ -0.267 │ [-0.433, -0.133] │ -0.050           │ REGRESSED
 context_precision          │    0.333 │   0.244 │ -0.089 │ [-0.144, -0.044] │ -0.050           │ REGRESSED
 ndcg                       │    1.000 │   0.733 │ -0.267 │ [-0.433, -0.133] │ -0.030           │ REGRESSED
 token_overlap_faithfulness │    1.000 │   0.567 │ -0.433 │ [-0.600, -0.267] │ -0.050, min 0.70 │ BELOW FLOOR
 rouge_l_recall             │    0.810 │   0.748 │ -0.062 │ [-0.200, +0.051] │ -0.081           │ pass

Items that got worse:
 item                 ┃ worst delta ┃ metrics that dropped
━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 q01-pto              │      -1.000 │ context_recall, context_precision, ndcg, token_overlap_faithfulness
 q04-parental         │      -1.000 │ context_recall, context_precision, ndcg, token_overlap_faithfulness
 q05-remote           │      -1.000 │ context_recall, context_precision, ndcg, token_overlap_faithfulness
 q08-expense-deadline │      -1.000 │ context_recall, context_precision, ndcg, token_overlap_faithfulness
 q09-travel-class     │      -1.000 │ context_recall, context_precision, ndcg, token_overlap_faithfulness
 q21-laptop           │      -1.000 │ context_recall, context_precision, ndcg, token_overlap_faithfulness
 q24-badge            │      -1.000 │ context_recall, context_precision, ndcg, token_overlap_faithfulness
 q25-holiday          │      -1.000 │ context_recall, context_precision, ndcg, token_overlap_faithfulness
 q06-stipend          │      -1.000 │ token_overlap_faithfulness
 q07-expense          │      -1.000 │ token_overlap_faithfulness
```

Run it on `examples/good_run.jsonl` instead and it passes, even though NDCG fell past its margin, because that drop comes from 3 questions and the confidence interval still includes zero:

```text
rag-eval-gate PASS: 0 failing of 5 metrics
30 items, paired bootstrap 2000 samples at 95%, baseline dataset 379945e1679b
 metric                     ┃ baseline ┃ current ┃  delta ┃ 95% CI           ┃ allowed          ┃ result
━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━
 context_recall             │    1.000 │   1.000 │ +0.000 │ [+0.000, +0.000] │ -0.050           │ pass
 context_precision          │    0.333 │   0.333 │ +0.000 │ [+0.000, +0.000] │ -0.050           │ pass
 ndcg                       │    1.000 │   0.963 │ -0.037 │ [-0.086, +0.000] │ -0.030           │ pass (drop within noise)
 token_overlap_faithfulness │    1.000 │   1.000 │ +0.000 │ [+0.000, +0.000] │ -0.050, min 0.70 │ pass
 rouge_l_recall             │    0.810 │   0.810 │ +0.000 │ [+0.000, +0.000] │ -0.081           │ pass

Items that got worse:
 item          ┃ worst delta ┃ metrics that dropped
━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━
 q01-pto       │      -0.369 │ ndcg
 q02-pto-carry │      -0.369 │ ndcg
 q14-health    │      -0.369 │ ndcg
```

Exit codes: `0` pass · `1` gate failed · `2` bad input or config.

## Why

Fixed thresholds ("faithfulness ≥ 0.8") don't answer the question a reviewer actually has: **did this PR make things worse?** rag-eval-gate answers that question:

- **Compared with a baseline, not a fixed number.** Each metric gets its own allowed drop (absolute `max_drop` or relative `max_drop_rel`), plus an optional hard floor (`min`).
- **Noise-aware.** A paired bootstrap over per-question score changes gives a confidence interval for the drop. A metric fails only when the mean drop exceeds the margin **and** the interval excludes zero. Floors are never softened.
- **Points at the questions.** The report lists the questions that got worse and which metrics fell, so you can debug the regression rather than just learn it happened.
- **Refuses to compare apples with oranges.** The baseline stores a SHA-256 fingerprint of the dataset. Missing, extra or duplicate question IDs, a changed dataset, or fewer than `min_items` questions exit 2.
- **Fits CI.** Console, Markdown and JSON reports, a reusable GitHub Action with a job summary and an optional sticky PR comment.

### Where continuous-eval ends and this project begins

| continuous-eval (dependency) | rag-eval-gate (this repo) |
|---|---|
| Metric math: chunk precision, recall and F1; MAP, MRR, NDCG; ROUGE, token-overlap and BLEU faithfulness and correctness | Baseline files and promotion, dataset fingerprinting, ID coverage checks |
| | Per-metric margins, floors, `error`/`warn` severity |
| | Paired-bootstrap noise test and per-question regression list |
| | Reports, exit codes, CLI, GitHub Action |
| | Telemetry off by default; graceful scoring of empty answers or context (upstream raises) |

Every score comes from continuous-eval's public metric classes. Nothing is vendored or patched.

## Inputs

**`dataset.jsonl`**, one question per line:

```json
{"id": "q01-pto", "question": "How much PTO do full-time employees accrue?",
 "ground_truth_context": ["Full-time employees accrue 1.5 days of paid time off per month, up to 30 days."],
 "ground_truth_answers": ["1.5 days per month, capped at 30 days."]}
```

**`run.jsonl`**, your app's output for each question ID (ranked context first):

```json
{"id": "q01-pto", "retrieved_context": ["Full-time employees accrue ...", "The cafeteria is open ..."], "answer": "..."}
```

**`gate.yaml`**:

```yaml
# Which metrics block a merge, and by how much they may drop versus the baseline.
# A metric fails only if the mean drop exceeds the margin AND the paired bootstrap
# confidence interval of the drop excludes zero (so a few noisy items don't block).
metrics:
  context_recall:             {max_drop: 0.05}
  context_precision:          {max_drop: 0.05}
  ndcg:                       {max_drop: 0.03}
  token_overlap_faithfulness: {max_drop: 0.05, min: 0.70}
  rouge_l_recall:             {max_drop_rel: 0.10, severity: warn}

bootstrap: {samples: 2000, confidence: 0.95, seed: 7}
min_items: 20      # refuse to gate on fewer items (exit 2)
item_drop: 0.10    # list items whose score fell by at least this much
max_items_listed: 10
```

## Workflow

```bash
# 1. Score a known-good run and promote it to the baseline (commit baseline.json)
reg score -d dataset.jsonl -r run.jsonl -o scores.json
reg baseline promote scores.json -o baseline.json --note "main @ abc123"

# 2. In every PR: produce run.jsonl from your app, then gate it
reg gate -d dataset.jsonl -r run.jsonl -b baseline.json -g gate.yaml -f markdown -o report.md

# Other commands
reg compare -b baseline.json -s scores.json -g gate.yaml   # compare two existing score files
reg list-metrics                                          # the metric catalogue
```

### GitHub Action

```yaml
permissions:
  contents: read
  pull-requests: write      # only needed for comment: "true"

steps:
  - uses: actions/checkout@v4
  - run: python my_app/eval_run.py > run.jsonl      # your app answers the eval questions
  - uses: rvspraveen/rag-eval-gate@v0.1.0
    with:
      dataset: evals/dataset.jsonl
      run: run.jsonl
      baseline: evals/baseline.json
      gate: evals/gate.yaml
      comment: "true"
```

Outputs: `report` (Markdown path) and `scores` (fresh scores, ready to promote when you accept a change).

## Metrics

| Metric | What it measures | continuous-eval class |
|---|---|---|
| `context_precision` | Share of retrieved chunks that match a gold chunk | `PrecisionRecallF1` |
| `context_recall` | Share of gold chunks that were retrieved | `PrecisionRecallF1` |
| `context_f1` | Harmonic mean of context precision and recall | `PrecisionRecallF1` |
| `average_precision` | Mean average precision of the ranked context | `RankedRetrievalMetrics` |
| `reciprocal_rank` | 1 / rank of the first relevant chunk | `RankedRetrievalMetrics` |
| `ndcg` | Normalised discounted cumulative gain of the ranked context | `RankedRetrievalMetrics` |
| `rouge_faithfulness` | Answer sentences supported by context (ROUGE-L) | `DeterministicFaithfulness` |
| `token_overlap_faithfulness` | Answer sentences supported by context (token overlap) | `DeterministicFaithfulness` |
| `bleu_faithfulness` | Answer sentences supported by context (BLEU) | `DeterministicFaithfulness` |
| `rouge_l_recall` | Reference answer covered by the answer (ROUGE-L recall) | `DeterministicAnswerCorrectness` |
| `token_overlap_recall` | Reference answer tokens present in the answer | `DeterministicAnswerCorrectness` |
| `token_overlap_f1` | Token overlap F1 against the reference answer | `DeterministicAnswerCorrectness` |

## Telemetry

continuous-eval sends anonymous usage events to PostHog unless `CONTINUOUS_EVAL_DO_NOT_TRACK=true`. **rag-eval-gate sets this for you** when it is imported, before continuous-eval loads, and a test checks it. `reg setup` is the only command that touches the network.

## Limitations

The metrics are lexical, the noise test can hide a small but consistent regression, and the upstream caps Python at 3.12. Read [LIMITATIONS.md](LIMITATIONS.md) before relying on it.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md). CI runs ruff, pytest (coverage ≥ 90%) on Python 3.10 to 3.12, bandit, pip-audit, CodeQL, and a dogfood job: the healthy sample run must pass and the regressed run must fail. Security notes are in [SECURITY.md](SECURITY.md).

## Credits

- [continuous-eval](https://github.com/relari-ai/continuous-eval) by Relari (Yi Zhang, Pasquale Antonante and contributors), Apache-2.0. All metric computation. Used as a pinned dependency, not modified.
- Sample data describes a fictional company and is generated by `examples/make_samples.py`.

See [NOTICE](NOTICE) for full attribution. rag-eval-gate is released under the [MIT License](LICENSE).
