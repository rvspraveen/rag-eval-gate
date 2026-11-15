from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def examples(tmp_path: Path) -> Path:
    """A private copy of the bundled examples."""
    dst = tmp_path / "examples"
    shutil.copytree(EXAMPLES, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def make_scores(values: dict[str, list[float]], sha: str = "a" * 64, kind: str = "scores") -> dict:
    """Build a scores dict directly (no upstream call) for comparator tests."""
    names = list(values)
    n = len(next(iter(values.values())))
    items = {f"i{k:03d}": {m: values[m][k] for m in names} for k in range(n)}
    return {
        "schema": "rag-eval-gate/scores@1",
        "kind": kind,
        "dataset_sha256": sha,
        "n_items": n,
        "metrics": names,
        "aggregate": {m: sum(v) / n for m, v in values.items()},
        "items": items,
    }


def write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path
