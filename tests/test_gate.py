from __future__ import annotations

import pytest

from reg.errors import ConfigError
from reg.gate import Rule, load_gate


def _write(tmp_path, text):
    p = tmp_path / "gate.yaml"
    p.write_text(text)
    return p


def test_example_gate_loads(examples):
    g = load_gate(examples / "gate.yaml")
    assert g.metrics["rouge_l_recall"].severity == "warn"
    assert g.metrics["token_overlap_faithfulness"].min == 0.70
    assert g.min_items == 20


@pytest.mark.parametrize(
    ("text", "match"),
    [
        ("metrics: {}\n", "metrics"),
        ("metrics:\n  ndcg: {max_drop: 0.1, max_drop_rel: 0.1}\n", "either max_drop or max_drop_rel"),
        ("metrics:\n  ndcg: {}\n", "needs max_drop"),
        ("metrics:\n  ndcg: {max_dorp: 0.1}\n", "max_dorp"),
        ("metrics:\n  ndcg: {max_drop: -1}\n", "max_drop"),
        ("metrics:\n  not_a_metric: {max_drop: 0.1}\n", "unknown metric"),
        ("metrics:\n  ndcg: {max_drop: 0.1}\nextra: 1\n", "extra"),
        ("- a\n- b\n", "mapping"),
        ("metrics: [\n", "invalid YAML"),
    ],
)
def test_bad_gates(tmp_path, text, match):
    with pytest.raises(ConfigError, match=match):
        load_gate(_write(tmp_path, text))


def test_missing_gate(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_gate(tmp_path / "nope.yaml")


def test_margins():
    assert Rule(max_drop=0.05).margin(0.8) == 0.05
    assert Rule(max_drop_rel=0.1).margin(0.8) == pytest.approx(0.08)
    assert Rule(min=0.5).margin(0.8) is None
