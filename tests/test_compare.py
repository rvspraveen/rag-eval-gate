from __future__ import annotations

import numpy as np
import pytest

from reg.compare import FLOOR, NOISE, OK, REGRESSED, bootstrap_ci, compare
from reg.errors import ConfigError, InputError
from reg.gate import Gate

from .conftest import make_scores

N = 30


def gate(**rules) -> Gate:
    return Gate.model_validate({"metrics": rules or {"ndcg": {"max_drop": 0.03}}, "min_items": 20})


def test_identical_runs_pass():
    b = make_scores({"ndcg": [1.0] * N})
    c = compare(b, b, gate())
    assert c.passed() and c.results[0].status == OK
    assert c.results[0].ci_low == c.results[0].ci_high == 0.0
    assert c.worst_items == []


def test_improvement_passes():
    b = make_scores({"ndcg": [0.5] * N})
    s = make_scores({"ndcg": [0.9] * N})
    assert compare(b, s, gate()).passed()


def test_consistent_drop_regresses():
    b = make_scores({"ndcg": [1.0] * N})
    s = make_scores({"ndcg": [0.9] * N})
    c = compare(b, s, gate())
    r = c.results[0]
    assert r.status == REGRESSED and r.failed and not c.passed()
    assert r.delta == pytest.approx(-0.1)
    assert len(c.errors) == 1


def test_few_items_drop_is_noise():
    # 3 of 30 items lose 0.37 each: mean drop 0.037 > margin 0.03, but the CI touches zero.
    vals = [1.0] * N
    for k in (0, 1, 2):
        vals[k] = 0.63
    c = compare(make_scores({"ndcg": [1.0] * N}), make_scores({"ndcg": vals}), gate())
    r = c.results[0]
    assert r.delta < -0.03
    assert r.status == NOISE and not r.failed and c.passed()
    assert [i.item for i in c.worst_items] == ["i000", "i001", "i002"]


def test_floor_breach_even_without_drop():
    b = make_scores({"ndcg": [0.6] * N})
    c = compare(b, b, gate(ndcg={"min": 0.7}))
    assert c.results[0].status == FLOOR and not c.passed()


def test_relative_margin():
    b = make_scores({"ndcg": [0.5] * N})
    s = make_scores({"ndcg": [0.47] * N})  # drop 0.03 < 10% of 0.5
    assert compare(b, s, gate(ndcg={"max_drop_rel": 0.1})).passed()
    s = make_scores({"ndcg": [0.44] * N})  # drop 0.06 > 0.05
    assert not compare(b, s, gate(ndcg={"max_drop_rel": 0.1})).passed()


def test_warn_severity_only_fails_with_flag():
    b = make_scores({"ndcg": [1.0] * N})
    s = make_scores({"ndcg": [0.5] * N})
    c = compare(b, s, gate(ndcg={"max_drop": 0.03, "severity": "warn"}))
    assert c.passed() and not c.passed(fail_on_warn=True)
    assert len(c.warnings) == 1 and not c.errors
    assert c.to_dict(fail_on_warn=True)["passed"] is False


def test_worst_items_grouped_and_capped():
    b = make_scores({"ndcg": [1.0] * N, "context_recall": [1.0] * N})
    s = make_scores({"ndcg": [0.0] * 15 + [1.0] * 15, "context_recall": [0.0] * 15 + [1.0] * 15})
    g = Gate.model_validate(
        {"metrics": {"ndcg": {"max_drop": 0.03}, "context_recall": {"max_drop": 0.03}}, "max_items_listed": 4, "min_items": 20}
    )
    c = compare(b, s, g)
    assert len(c.worst_items) == 4
    assert set(c.worst_items[0].drops) == {"ndcg", "context_recall"}
    d = c.to_dict()
    assert d["worst_items"][0]["drops"]["ndcg"] == {"baseline": 1.0, "current": 0.0}


def test_different_dataset_rejected():
    b = make_scores({"ndcg": [1.0] * N}, sha="a" * 64)
    s = make_scores({"ndcg": [1.0] * N}, sha="b" * 64)
    with pytest.raises(InputError, match="different dataset"):
        compare(b, s, gate())


def test_item_mismatch_rejected():
    b = make_scores({"ndcg": [1.0] * N})
    s = make_scores({"ndcg": [1.0] * (N + 1)})
    with pytest.raises(InputError, match="1 unexpected"):
        compare(b, s, gate())


def test_min_items():
    b = make_scores({"ndcg": [1.0] * 5})
    with pytest.raises(InputError, match="min_items=20"):
        compare(b, b, gate())


def test_gate_metric_missing_from_scores():
    b = make_scores({"ndcg": [1.0] * N})
    with pytest.raises(ConfigError, match="'context_recall' is not in the baseline"):
        compare(b, b, gate(context_recall={"max_drop": 0.1}))


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda d: d.update(schema="other"), "not a rag-eval-gate scores file"),
        (lambda d: d.pop("items"), "missing 'items'"),
        (lambda d: d.update(items={}), "non-empty"),
        (lambda d: d["items"]["i000"].update(ndcg="x"), "no numeric value"),
        (lambda d: d["items"]["i000"].update(ndcg=True), "no numeric value"),
    ],
)
def test_malformed_scores(mutate, match):
    b = make_scores({"ndcg": [1.0] * N})
    s = make_scores({"ndcg": [1.0] * N})
    mutate(s)
    with pytest.raises(InputError, match=match):
        compare(b, s, gate())


def test_bootstrap_is_deterministic_and_brackets_mean():
    rng = np.random.default_rng(0)
    d = rng.normal(-0.05, 0.1, size=50)
    a = bootstrap_ci(d, 2000, 0.95, seed=7)
    assert a == bootstrap_ci(d, 2000, 0.95, seed=7)
    assert a[0] < d.mean() < a[1]
