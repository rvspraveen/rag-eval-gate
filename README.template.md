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
{{REGRESSED_OUTPUT}}
```

Run it on `examples/good_run.jsonl` instead and it passes, even though NDCG fell past its margin, because that drop comes from 3 questions and the confidence interval still includes zero:

```text
{{GOOD_OUTPUT}}
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
{{GATE_YAML}}
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
{{METRIC_TABLE}}

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
