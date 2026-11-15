# Contributing

Thanks for helping! Small, focused PRs are easiest to review.

```bash
python -m venv .venv && source .venv/bin/activate   # Python 3.10 to 3.12
pip install -e ".[dev]"
reg setup                   # one-time NLTK download
ruff check . && ruff format --check .
pytest                      # coverage must stay >= 90%
bandit -q -r src
```

**Adding a metric**
1. If continuous-eval already computes it, add an entry to `METRICS` in `src/reg/metrics.py` (and a `GROUPS` entry if it uses a new upstream class). Use only continuous-eval's public classes.
2. Add a test in `tests/test_metrics.py` that calls the real upstream metric.
3. Document it in the README metric table and `CHANGELOG.md`.

**Changing the samples**
Edit `examples/make_samples.py`, then regenerate everything:

```bash
python examples/make_samples.py
reg score -d examples/dataset.jsonl -r examples/baseline_run.jsonl -o /tmp/s.json
reg baseline promote /tmp/s.json -o examples/baseline.json
```

Sample data must stay synthetic. CI fails if the committed samples or baseline drift from the generator.

**Upgrading continuous-eval**
It is pinned exactly. Bump it in its own PR; the dogfood job must still pass and fail on the bundled runs.
