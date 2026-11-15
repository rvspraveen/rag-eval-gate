"""Stable metric names mapped onto continuous-eval's public metric classes.

continuous-eval is imported lazily, only when scoring, so `reg compare` stays
fast and never touches the network.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from .errors import ConfigError, InputError
from .io import DatasetItem, RunItem


@dataclass(frozen=True)
class Group:
    module: str
    cls: str
    needs: str  # which inputs the group needs, used for validation and docs


GROUPS: dict[str, Group] = {
    "retrieval": Group("continuous_eval.metrics.retrieval", "PrecisionRecallF1", "retrieved + gold context"),
    "ranking": Group("continuous_eval.metrics.retrieval", "RankedRetrievalMetrics", "retrieved + gold context"),
    "faithfulness": Group(
        "continuous_eval.metrics.generation.text.deterministic", "DeterministicFaithfulness", "answer + retrieved context"
    ),
    "correctness": Group(
        "continuous_eval.metrics.generation.text.deterministic", "DeterministicAnswerCorrectness", "answer + gold answers"
    ),
}


@dataclass(frozen=True)
class MetricSpec:
    group: str
    key: str  # output key in the continuous-eval result dict
    description: str


METRICS: dict[str, MetricSpec] = {
    "context_precision": MetricSpec("retrieval", "context_precision", "Share of retrieved chunks that match a gold chunk"),
    "context_recall": MetricSpec("retrieval", "context_recall", "Share of gold chunks that were retrieved"),
    "context_f1": MetricSpec("retrieval", "context_f1", "Harmonic mean of context precision and recall"),
    "average_precision": MetricSpec("ranking", "average_precision", "Mean average precision of the ranked context"),
    "reciprocal_rank": MetricSpec("ranking", "reciprocal_rank", "1 / rank of the first relevant chunk"),
    "ndcg": MetricSpec("ranking", "ndcg", "Normalised discounted cumulative gain of the ranked context"),
    "rouge_faithfulness": MetricSpec("faithfulness", "rouge_faithfulness", "Answer sentences supported by context (ROUGE-L)"),
    "token_overlap_faithfulness": MetricSpec(
        "faithfulness", "token_overlap_faithfulness", "Answer sentences supported by context (token overlap)"
    ),
    "bleu_faithfulness": MetricSpec("faithfulness", "bleu_faithfulness", "Answer sentences supported by context (BLEU)"),
    "rouge_l_recall": MetricSpec("correctness", "rouge_l_recall", "Reference answer covered by the answer (ROUGE-L recall)"),
    "token_overlap_recall": MetricSpec("correctness", "token_overlap_recall", "Reference answer tokens present in the answer"),
    "token_overlap_f1": MetricSpec("correctness", "token_overlap_f1", "Token overlap F1 against the reference answer"),
}


def validate_names(names: list[str]) -> list[str]:
    unknown = [n for n in names if n not in METRICS]
    if unknown:
        raise ConfigError(f"unknown metric(s): {', '.join(unknown)}. Run `reg list-metrics` to see the catalogue.")
    if not names:
        raise ConfigError("no metrics selected")
    return list(dict.fromkeys(names))


def _check_inputs(groups: set[str], pairs: list[tuple[DatasetItem, RunItem]]) -> None:
    for d, _ in pairs:
        if groups & {"retrieval", "ranking"} and not d.ground_truth_context:
            raise InputError(f"item {d.id!r}: retrieval metrics need a non-empty ground_truth_context")
        if "correctness" in groups and not d.ground_truth_answers:
            raise InputError(f"item {d.id!r}: correctness metrics need a non-empty ground_truth_answers")


def _load(group: str) -> Any:
    g = GROUPS[group]
    return getattr(importlib.import_module(g.module), g.cls)()


def _run_group(group: str, metric: Any, d: DatasetItem, r: RunItem) -> dict[str, Any]:
    if group in ("retrieval", "ranking"):
        return metric(retrieved_context=r.retrieved_context, ground_truth_context=d.ground_truth_context)
    if group == "faithfulness":
        # Upstream raises on an empty answer or empty context; an unsupported
        # (or missing) answer is scored 0.0 here instead of crashing the gate.
        if not r.answer.strip() or not any(c.strip() for c in r.retrieved_context):
            return dict.fromkeys(("rouge_faithfulness", "token_overlap_faithfulness", "bleu_faithfulness"), 0.0)
        return metric(answer=r.answer, retrieved_context=r.retrieved_context)
    return metric(answer=r.answer, ground_truth_answers=d.ground_truth_answers)


def score_items(names: list[str], pairs: list[tuple[DatasetItem, RunItem]]) -> dict[str, dict[str, float]]:
    """Return {item_id: {metric: value}} using continuous-eval's public Metric API."""
    names = validate_names(names)
    groups = {METRICS[n].group for n in names}
    _check_inputs(groups, pairs)
    loaded = {g: _load(g) for g in sorted(groups)}
    out: dict[str, dict[str, float]] = {}
    for d, r in pairs:
        raw: dict[str, Any] = {}
        for g, metric in loaded.items():
            raw.update(_run_group(g, metric, d, r))
        out[d.id] = {n: round(float(raw[METRICS[n].key]), 6) for n in names}
    return out
