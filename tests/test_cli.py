from __future__ import annotations

import json

import pytest

from reg import __version__
from reg.cli import main


def run(examples, run_file, *extra):
    return main(
        [
            "gate",
            "-d",
            str(examples / "dataset.jsonl"),
            "-r",
            str(examples / run_file),
            "-b",
            str(examples / "baseline.json"),
            "-g",
            str(examples / "gate.yaml"),
            *extra,
        ]
    )


def test_good_run_passes(examples, capsys):
    assert run(examples, "good_run.jsonl") == 0
    out = capsys.readouterr().out
    assert "PASS" in out and "within noise" in out


def test_regressed_run_fails_on_expected_metrics(examples, tmp_path):
    out = tmp_path / "r.json"
    assert run(examples, "regressed_run.jsonl", "-f", "json", "-o", str(out)) == 1
    report = json.loads(out.read_text())
    failed = {m["metric"]: m["status"] for m in report["metrics"] if m["failed"]}
    assert failed == {
        "context_recall": "regressed",
        "context_precision": "regressed",
        "ndcg": "regressed",
        "token_overlap_faithfulness": "below_floor",
    }
    assert report["passed"] is False
    assert len(report["worst_items"]) == 10


def test_baseline_run_matches_baseline(examples):
    assert run(examples, "baseline_run.jsonl") == 0


def test_markdown_to_stdout(examples, capsys):
    assert run(examples, "regressed_run.jsonl", "-f", "markdown") == 1
    md = capsys.readouterr().out
    assert md.startswith("## ❌ rag-eval-gate FAIL: 4 failing of 5 metrics")
    assert "| `context_recall` | 1.000 | 0.733 |" in md
    assert "### Items that got worse" in md


def test_json_to_stdout(examples, capsys):
    assert run(examples, "good_run.jsonl", "-f", "json") == 0
    assert json.loads(capsys.readouterr().out)["passed"] is True


def test_markdown_file_and_scores_out(examples, tmp_path):
    md, sc = tmp_path / "out" / "r.md", tmp_path / "s.json"
    assert run(examples, "good_run.jsonl", "-f", "markdown", "-o", str(md), "--scores-out", str(sc)) == 0
    assert md.read_text().startswith("## ✅")
    assert json.loads(sc.read_text())["n_items"] == 30


def test_score_promote_compare_roundtrip(examples, tmp_path):
    s, b = tmp_path / "s.json", tmp_path / "b.json"
    assert (
        main(
            [
                "score",
                "-d",
                str(examples / "dataset.jsonl"),
                "-r",
                str(examples / "good_run.jsonl"),
                "-m",
                "ndcg,context_recall",
                "-o",
                str(s),
            ]
        )
        == 0
    )
    assert json.loads(s.read_text())["metrics"] == ["ndcg", "context_recall"]
    assert main(["baseline", "promote", str(s), "-o", str(b), "--note", "v1"]) == 0
    data = json.loads(b.read_text())
    assert data["kind"] == "baseline" and data["note"] == "v1"
    gate = tmp_path / "g.yaml"
    gate.write_text("metrics:\n  ndcg: {max_drop: 0.01}\n")
    assert main(["compare", "-b", str(b), "-s", str(s), "-g", str(gate)]) == 0


def test_committed_baseline_is_current(examples, tmp_path):
    s = tmp_path / "s.json"
    assert main(["score", "-d", str(examples / "dataset.jsonl"), "-r", str(examples / "baseline_run.jsonl"), "-o", str(s)]) == 0
    fresh = json.loads(s.read_text())
    committed = json.loads((examples / "baseline.json").read_text())
    assert fresh["items"] == committed["items"]
    assert fresh["dataset_sha256"] == committed["dataset_sha256"]


def test_warn_flag(examples, tmp_path):
    gate = tmp_path / "g.yaml"
    gate.write_text("metrics:\n  context_recall: {max_drop: 0.05, severity: warn}\nmin_items: 20\n")
    args = [
        "gate",
        "-d",
        str(examples / "dataset.jsonl"),
        "-r",
        str(examples / "regressed_run.jsonl"),
        "-b",
        str(examples / "baseline.json"),
        "-g",
        str(gate),
    ]
    assert main(args) == 0
    assert main([*args, "--fail-on-warn"]) == 1


@pytest.mark.parametrize(
    "argv",
    [
        ["gate", "-d", "nope.jsonl", "-r", "x", "-b", "x", "-g", "x"],
        ["score", "-d", "x", "-r", "x", "-o", "x", "-m", "bogus"],
        ["compare", "-b", "nope.json", "-s", "nope.json", "-g", "nope.yaml"],
        ["frobnicate"],
        [],
    ],
)
def test_usage_errors_exit_2(argv, capsys):
    assert main(argv) == 2


def test_wrong_dataset_exit_2(examples, tmp_path):
    d = tmp_path / "d.jsonl"
    d.write_text((examples / "dataset.jsonl").read_text().replace("How much PTO", "How much leave"))
    args = [
        "gate",
        "-d",
        str(d),
        "-r",
        str(examples / "good_run.jsonl"),
        "-b",
        str(examples / "baseline.json"),
        "-g",
        str(examples / "gate.yaml"),
    ]
    assert main(args) == 2


def test_list_metrics(capsys):
    assert main(["list-metrics"]) == 0
    out = capsys.readouterr().out
    assert "context_recall" in out and "DeterministicFaithfulness" in out


def test_version(capsys):
    assert main(["--version"]) == 0
    assert __version__ in capsys.readouterr().out
