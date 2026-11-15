"""Scores and baseline files."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any

from . import UPSTREAM, __version__
from .errors import InputError
from .io import dataset_fingerprint, join, load_dataset, load_run
from .metrics import METRICS, score_items

SCHEMA = "rag-eval-gate/scores@1"


def upstream_version() -> str:
    try:
        return version(UPSTREAM)
    except PackageNotFoundError:  # pragma: no cover - only without the dependency installed
        return "unknown"


def score(dataset_path: str, run_path: str, metrics: list[str] | None = None) -> dict[str, Any]:
    dataset = load_dataset(dataset_path)
    run = load_run(run_path)
    pairs = join(dataset, run)
    names = metrics or list(METRICS)
    items = score_items(names, pairs)
    n = len(items)
    aggregate = {m: round(sum(v[m] for v in items.values()) / n, 6) for m in names}
    return {
        "schema": SCHEMA,
        "kind": "scores",
        "tool": f"rag-eval-gate {__version__}",
        "upstream": f"{UPSTREAM} {upstream_version()}",
        "dataset_sha256": dataset_fingerprint(dataset),
        "n_items": n,
        "metrics": list(names),
        "aggregate": aggregate,
        "items": items,
    }


def validate_scores(data: dict[str, Any], label: str) -> dict[str, Any]:
    if data.get("schema") != SCHEMA:
        raise InputError(f"{label}: not a rag-eval-gate scores file (schema {data.get('schema')!r}, expected {SCHEMA!r})")
    for key in ("dataset_sha256", "metrics", "items"):
        if key not in data:
            raise InputError(f"{label}: missing {key!r}")
    items = data["items"]
    if not isinstance(items, dict) or not items:
        raise InputError(f"{label}: 'items' must be a non-empty object")
    for item_id, vals in items.items():
        for m in data["metrics"]:
            v = vals.get(m) if isinstance(vals, dict) else None
            if not isinstance(v, int | float) or isinstance(v, bool):
                raise InputError(f"{label}: item {item_id!r} has no numeric value for {m!r}")
    return data


def promote(data: dict[str, Any], note: str | None = None) -> dict[str, Any]:
    data = dict(validate_scores(data, "scores"))
    data["kind"] = "baseline"
    if note:
        data["note"] = note
    return data
