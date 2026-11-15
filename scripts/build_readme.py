"""Render README.md from README.template.md using real command output.

    python scripts/build_readme.py

Run after any change that affects CLI output, so the README never shows made-up results.
"""

from __future__ import annotations

import os
import re

# Runs this repo's own CLI with fixed arguments.
import subprocess  # nosec B404
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_gate(run_file: str) -> str:
    cmd = [sys.executable, "-m", "reg", "gate", "-d", "examples/dataset.jsonl", "-r", f"examples/{run_file}"]
    cmd += ["-b", "examples/baseline.json", "-g", "examples/gate.yaml"]
    env = {**os.environ, "COLUMNS": "132", "NO_COLOR": "1", "TERM": "dumb"}
    p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env, check=False)  # noqa: S603  # nosec B603
    expected = 1 if run_file.startswith("regressed") else 0
    if p.returncode != expected:
        raise SystemExit(f"{run_file}: expected exit {expected}, got {p.returncode}\n{p.stderr}")
    return "\n".join(line.rstrip() for line in p.stdout.splitlines())


def metric_table() -> str:
    from reg.metrics import GROUPS, METRICS

    return "\n".join(f"| `{n}` | {s.description} | `{GROUPS[s.group].cls}` |" for n, s in METRICS.items())


def gate_yaml() -> str:
    text = (ROOT / "examples" / "gate.yaml").read_text(encoding="utf-8")
    return re.sub(r"\n+$", "", text)


def main() -> None:
    out = (ROOT / "README.template.md").read_text(encoding="utf-8")
    out = out.replace("{{REGRESSED_OUTPUT}}", run_gate("regressed_run.jsonl"))
    out = out.replace("{{GOOD_OUTPUT}}", run_gate("good_run.jsonl"))
    out = out.replace("{{METRIC_TABLE}}", metric_table())
    out = out.replace("{{GATE_YAML}}", gate_yaml())
    (ROOT / "README.md").write_text(out, encoding="utf-8")
    print("README.md rendered")


if __name__ == "__main__":
    main()
