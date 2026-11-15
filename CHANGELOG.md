# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-12

### Added
- `reg score`, `reg baseline promote`, `reg compare`, `reg gate`, `reg list-metrics`, `reg setup`.
- 12 offline metrics through continuous-eval's public API: retrieval (precision, recall, F1), ranking (MAP, MRR, NDCG), faithfulness (ROUGE, token overlap, BLEU) and correctness (ROUGE-L recall, token overlap recall and F1).
- Baseline comparison with per-metric absolute or relative margins, hard floors and `error`/`warn` severity.
- Noise-aware gating with a seeded paired bootstrap over per-item deltas.
- Per-question regression list, grouped by item.
- Coverage checks: duplicate, missing or unexpected IDs across dataset, run and baseline; dataset fingerprint check against the baseline; `min_items` guard.
- Console, Markdown and JSON reports; exit codes 0 / 1 / 2.
- Composite GitHub Action with job summary and optional sticky PR comment.
- Synthetic, regenerable sample dataset with healthy, noisy and regressed runs.
- Telemetry from continuous-eval disabled by default.
