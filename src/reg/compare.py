"""Baseline comparison with noise-aware (paired bootstrap) gating."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from .errors import ConfigError, InputError
from .gate import Gate
from .io import id_mismatch
from .scores import validate_scores

OK = "ok"
NOISE = "within_noise"  # dropped past the margin, but not distinguishable from noise
REGRESSED = "regressed"
FLOOR = "below_floor"


@dataclass
class MetricResult:
    metric: str
    baseline: float
    current: float
    delta: float
    ci_low: float
    ci_high: float
    margin: float | None
    floor: float | None
    severity: str
    status: str

    @property
    def failed(self) -> bool:
        return self.status in (REGRESSED, FLOOR)


@dataclass
class ItemRegression:
    """One question whose score fell on one or more gated metrics."""

    item: str
    drops: dict[str, tuple[float, float]]  # metric -> (baseline, current)

    @property
    def worst_delta(self) -> float:
        return min(c - b for b, c in self.drops.values())


@dataclass
class Comparison:
    n_items: int
    confidence: float
    samples: int
    baseline_sha: str
    results: list[MetricResult]
    worst_items: list[ItemRegression] = field(default_factory=list)

    @property
    def errors(self) -> list[MetricResult]:
        return [r for r in self.results if r.failed and r.severity == "error"]

    @property
    def warnings(self) -> list[MetricResult]:
        return [r for r in self.results if r.failed and r.severity == "warn"]

    def passed(self, fail_on_warn: bool = False) -> bool:
        return not self.errors and not (fail_on_warn and self.warnings)

    def to_dict(self, fail_on_warn: bool = False) -> dict[str, Any]:
        return {
            "passed": self.passed(fail_on_warn),
            "n_items": self.n_items,
            "bootstrap": {"samples": self.samples, "confidence": self.confidence},
            "baseline_dataset_sha256": self.baseline_sha,
            "metrics": [asdict(r) | {"failed": r.failed} for r in self.results],
            "worst_items": [
                {
                    "item": i.item,
                    "worst_delta": round(i.worst_delta, 6),
                    "drops": {m: {"baseline": b, "current": c} for m, (b, c) in i.drops.items()},
                }
                for i in self.worst_items
            ],
        }


def bootstrap_ci(deltas: np.ndarray, samples: int, confidence: float, seed: int) -> tuple[float, float]:
    """Percentile bootstrap CI for the mean of paired per-item deltas."""
    if np.allclose(deltas, deltas[0]):
        v = float(deltas[0])
        return v, v
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(deltas), size=(samples, len(deltas)))
    means = deltas[idx].mean(axis=1)
    alpha = (1 - confidence) / 2
    lo, hi = np.quantile(means, [alpha, 1 - alpha])
    return float(lo), float(hi)


def compare(baseline: dict[str, Any], current: dict[str, Any], gate: Gate) -> Comparison:
    validate_scores(baseline, "baseline")
    validate_scores(current, "scores")
    if baseline["dataset_sha256"] != current["dataset_sha256"]:
        raise InputError("baseline was scored on a different dataset (dataset_sha256 differs). Re-score and promote a new baseline.")
    problem = id_mismatch(set(baseline["items"]), set(current["items"]), "scores do not match the baseline items")
    if problem:
        raise InputError(problem)
    ids = sorted(baseline["items"])
    if len(ids) < gate.min_items:
        raise InputError(f"only {len(ids)} items; the gate needs at least min_items={gate.min_items} for a meaningful comparison")

    results: list[MetricResult] = []
    drops: dict[str, dict[str, tuple[float, float]]] = {}
    bs = gate.bootstrap
    for metric, rule in gate.metrics.items():
        for label, data in (("baseline", baseline), ("scores", current)):
            if metric not in data["metrics"]:
                raise ConfigError(f"gate metric {metric!r} is not in the {label} file")
        b = np.array([baseline["items"][i][metric] for i in ids], dtype=float)
        c = np.array([current["items"][i][metric] for i in ids], dtype=float)
        d = c - b
        mean_b, mean_c, delta = float(b.mean()), float(c.mean()), float(d.mean())
        lo, hi = bootstrap_ci(d, bs.samples, bs.confidence, bs.seed)
        margin = rule.margin(mean_b)
        if rule.min is not None and mean_c < rule.min:
            status = FLOOR
        elif margin is not None and delta < -margin:
            status = REGRESSED if hi < 0 else NOISE
        else:
            status = OK
        res = MetricResult(
            metric=metric,
            baseline=round(mean_b, 4),
            current=round(mean_c, 4),
            delta=round(delta, 4),
            ci_low=round(lo, 4),
            ci_high=round(hi, 4),
            margin=None if margin is None else round(margin, 4),
            floor=rule.min,
            severity=rule.severity,
            status=status,
        )
        results.append(res)
        if res.status != OK:
            for k, i in enumerate(ids):
                if d[k] <= -gate.item_drop:
                    drops.setdefault(i, {})[metric] = (round(float(b[k]), 4), round(float(c[k]), 4))

    worst = sorted((ItemRegression(i, m) for i, m in drops.items()), key=lambda x: (x.worst_delta, -len(x.drops), x.item))
    return Comparison(
        n_items=len(ids),
        confidence=bs.confidence,
        samples=bs.samples,
        baseline_sha=baseline["dataset_sha256"],
        results=results,
        worst_items=worst[: gate.max_items_listed],
    )
