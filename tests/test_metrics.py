"""These tests call continuous-eval for real (offline metrics only)."""

from __future__ import annotations

import os

import pytest

from reg.errors import ConfigError, InputError
from reg.io import DatasetItem, RunItem
from reg.metrics import GROUPS, METRICS, score_items, validate_names

GOLD = "Full-time employees accrue 1.5 days of paid time off per month."
OTHER = "The cafeteria is open from 8am to 2pm on weekdays."


def pair(ctx, answer=GOLD, gt_ctx=(GOLD,), gt_ans=("1.5 days per month.",), i="a"):
    return (
        DatasetItem(id=i, question="q", ground_truth_context=list(gt_ctx), ground_truth_answers=list(gt_ans)),
        RunItem(id=i, retrieved_context=list(ctx), answer=answer),
    )


def test_telemetry_disabled_before_upstream_import():
    assert os.environ["CONTINUOUS_EVAL_DO_NOT_TRACK"] == "true"
    from continuous_eval.utils import telemetry  # upstream module, read-only check

    assert telemetry.telemetry._client.disabled is True


def test_catalogue_points_at_real_upstream_classes():
    import importlib

    for g in GROUPS.values():
        assert hasattr(importlib.import_module(g.module), g.cls)
    assert {m.group for m in METRICS.values()} == set(GROUPS)


def test_perfect_vs_missing_retrieval():
    names = ["context_recall", "context_precision", "ndcg", "token_overlap_faithfulness"]
    out = score_items(names, [pair([GOLD, OTHER], i="good"), pair([OTHER], i="bad")])
    assert out["good"]["context_recall"] == 1.0
    assert out["good"]["context_precision"] == 0.5
    assert out["good"]["token_overlap_faithfulness"] == 1.0
    assert out["bad"]["context_recall"] == 0.0
    assert out["bad"]["ndcg"] == 0.0


def test_rank_matters_for_ndcg_not_recall():
    out = score_items(["context_recall", "ndcg"], [pair([OTHER, GOLD])])
    assert out["a"]["context_recall"] == 1.0
    assert 0 < out["a"]["ndcg"] < 1


@pytest.mark.parametrize(("ctx", "answer"), [([GOLD], ""), ([], GOLD), (["  "], GOLD)])
def test_faithfulness_degenerate_inputs_score_zero(ctx, answer):
    # Upstream raises on these; we score them 0 instead of crashing the gate.
    out = score_items(["token_overlap_faithfulness", "rouge_faithfulness"], [pair(ctx, answer=answer)])
    assert out["a"] == {"token_overlap_faithfulness": 0.0, "rouge_faithfulness": 0.0}


def test_correctness():
    out = score_items(["token_overlap_recall"], [pair([GOLD], answer="It is 1.5 days per month.")])
    assert out["a"]["token_overlap_recall"] == 1.0


def test_missing_ground_truth_is_input_error():
    with pytest.raises(InputError, match="ground_truth_context"):
        score_items(["ndcg"], [pair([GOLD], gt_ctx=())])
    with pytest.raises(InputError, match="ground_truth_answers"):
        score_items(["token_overlap_f1"], [pair([GOLD], gt_ans=())])


def test_validate_names():
    assert validate_names(["ndcg", "ndcg"]) == ["ndcg"]
    with pytest.raises(ConfigError, match="unknown metric"):
        validate_names(["nope"])
    with pytest.raises(ConfigError, match="no metrics"):
        validate_names([])
