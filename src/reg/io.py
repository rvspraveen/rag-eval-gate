"""Loading and joining eval datasets and app runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import InputError


class DatasetItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    question: str
    ground_truth_context: list[str] = Field(default_factory=list)
    ground_truth_answers: list[str] = Field(default_factory=list)


class RunItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(min_length=1)
    retrieved_context: list[str] = Field(default_factory=list)
    answer: str = ""


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        raise InputError(f"file not found: {p}")
    rows: list[dict[str, Any]] = []
    for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            raise InputError(f"{p}:{n}: invalid JSON ({e.msg})") from e
        if not isinstance(row, dict):
            raise InputError(f"{p}:{n}: each line must be a JSON object")
        rows.append(row)
    if not rows:
        raise InputError(f"{p}: no records")
    return rows


def _parse(rows: list[dict[str, Any]], model: type[BaseModel], path: str | Path) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for n, row in enumerate(rows, start=1):
        try:
            item = model.model_validate(row)
        except ValidationError as e:
            first = e.errors()[0]
            loc = ".".join(str(x) for x in first["loc"])
            raise InputError(f"{path}: record {n}: {loc}: {first['msg']}") from e
        if item.id in out:  # type: ignore[attr-defined]
            raise InputError(f"{path}: duplicate id {item.id!r}")  # type: ignore[attr-defined]
        out[item.id] = item  # type: ignore[attr-defined]
    return out


def load_dataset(path: str | Path) -> dict[str, DatasetItem]:
    return _parse(read_jsonl(path), DatasetItem, path)


def load_run(path: str | Path) -> dict[str, RunItem]:
    return _parse(read_jsonl(path), RunItem, path)


def id_mismatch(expected: set[str], got: set[str], what: str) -> str | None:
    """Describe missing/extra IDs, or None when the sets match."""
    missing = sorted(expected - got)
    extra = sorted(got - expected)
    if not missing and not extra:
        return None
    parts = []
    if missing:
        parts.append(f"{len(missing)} missing ({', '.join(missing[:5])}{', ...' if len(missing) > 5 else ''})")
    if extra:
        parts.append(f"{len(extra)} unexpected ({', '.join(extra[:5])}{', ...' if len(extra) > 5 else ''})")
    return f"{what}: " + "; ".join(parts)


def join(dataset: dict[str, DatasetItem], run: dict[str, RunItem]) -> list[tuple[DatasetItem, RunItem]]:
    problem = id_mismatch(set(dataset), set(run), "run does not cover the dataset")
    if problem:
        raise InputError(problem)
    return [(dataset[i], run[i]) for i in sorted(dataset)]


def dataset_fingerprint(dataset: dict[str, DatasetItem]) -> str:
    """Order- and whitespace-independent hash of the dataset content."""
    canon = json.dumps([dataset[i].model_dump() for i in sorted(dataset)], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def read_json(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_file():
        raise InputError(f"file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise InputError(f"{p}: invalid JSON ({e.msg})") from e
    if not isinstance(data, dict):
        raise InputError(f"{p}: expected a JSON object")
    return data


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
