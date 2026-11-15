# Security policy

## Reporting a vulnerability

Please report vulnerabilities privately using GitHub's **Report a vulnerability** button (Security tab). Please don't open a public issue. We aim to reply within 5 working days.

## Scope notes

- `reg` reads local files and makes no network calls while scoring or comparing. `reg setup` is the only command that downloads anything (NLTK data from NLTK's servers).
- **Telemetry:** continuous-eval sends anonymous usage events to PostHog by default. `reg` sets `CONTINUOUS_EVAL_DO_NOT_TRACK=true` at package import, before continuous-eval loads, and a test asserts the PostHog client is disabled.
- Gate files are parsed with `yaml.safe_load` and validated with strict pydantic models (unknown keys are rejected).
- The GitHub Action passes all inputs through environment variables, never by interpolating them into shell commands. Only the optional PR-comment step uses a token, and it needs `pull-requests: write` granted by the calling workflow.
- CI runs bandit, pip-audit and CodeQL, and pins third-party actions to commit SHAs.

## Known advisory: json-repair GHSA-xf7x-x43h-rpqh

continuous-eval 0.3.14.post2 pins `json-repair <0.32`, and 0.31.0 is affected by GHSA-xf7x-x43h-rpqh (unbounded CPU use when following a circular `$ref` in a caller-supplied JSON schema, fixed in 0.60.1).

- continuous-eval calls `repair_json(text, return_objects=True)` without a schema, only when parsing LLM-judge output.
- rag-eval-gate v0.1 uses only deterministic metrics and never reaches that code.

CI ignores this single advisory by ID in `pip-audit`. The ignore will be removed when continuous-eval lifts the cap (we plan to propose that upstream).
