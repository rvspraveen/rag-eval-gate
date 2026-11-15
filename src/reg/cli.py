"""Command line interface: `reg`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from . import __version__
from .compare import Comparison, compare
from .errors import RegError
from .gate import load_gate
from .io import read_json, write_json
from .metrics import GROUPS, METRICS, validate_names
from .report import make_console, print_console, render_json, render_markdown
from .scores import promote, score

NLTK_PACKAGES = ("punkt", "punkt_tab", "stopwords")


def _emit(c: Comparison, fmt: str, out: str | None, fail_on_warn: bool) -> int:
    if fmt == "console" and not out:
        print_console(c, fail_on_warn)
    else:
        text = render_markdown(c, fail_on_warn) if fmt in ("markdown", "console") else render_json(c, fail_on_warn)
        if out:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_text(text, encoding="utf-8")
            print_console(c, fail_on_warn)
        else:
            sys.stdout.write(text)
    return 0 if c.passed(fail_on_warn) else 1


def _metrics_arg(value: str | None) -> list[str] | None:
    return validate_names([m.strip() for m in value.split(",") if m.strip()]) if value else None


def cmd_score(a: argparse.Namespace) -> int:
    data = score(a.dataset, a.run, _metrics_arg(a.metrics))
    write_json(a.out, data)
    Console(stderr=True).print(f"scored {data['n_items']} items on {len(data['metrics'])} metrics -> {a.out}")
    return 0


def cmd_promote(a: argparse.Namespace) -> int:
    write_json(a.out, promote(read_json(a.scores), a.note))
    Console(stderr=True).print(f"baseline written -> {a.out}")
    return 0


def cmd_compare(a: argparse.Namespace) -> int:
    gate = load_gate(a.gate)
    c = compare(read_json(a.baseline), read_json(a.scores), gate)
    return _emit(c, a.format, a.out, a.fail_on_warn)


def cmd_gate(a: argparse.Namespace) -> int:
    gate = load_gate(a.gate)
    baseline = read_json(a.baseline)
    current = score(a.dataset, a.run, list(gate.metrics))
    if a.scores_out:
        write_json(a.scores_out, current)
    c = compare(baseline, current, gate)
    return _emit(c, a.format, a.out, a.fail_on_warn)


def cmd_list(_: argparse.Namespace) -> int:
    t = Table(show_edge=False)
    for col in ("metric", "what it measures", "continuous-eval class", "needs"):
        t.add_column(col)
    for name, spec in METRICS.items():
        g = GROUPS[spec.group]
        t.add_row(name, spec.description, g.cls, g.needs)
    make_console().print(t)
    return 0


def cmd_setup(_: argparse.Namespace) -> int:  # pragma: no cover - network
    import nltk

    ok = all(nltk.download(p, quiet=True) for p in NLTK_PACKAGES)
    print("NLTK data ready" if ok else "NLTK download failed; check network or set NLTK_DATA", file=sys.stderr)
    return 0 if ok else 2


def _report_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--gate", "-g", required=True, help="gate.yaml")
    p.add_argument("--format", "-f", choices=["console", "markdown", "json"], default="console")
    p.add_argument("--out", "-o", help="write the report to a file (console summary still printed)")
    p.add_argument("--fail-on-warn", action="store_true", help="treat warn-severity failures as failures")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="reg", description="Baseline-aware merge gate for RAG quality (built on continuous-eval).")
    p.add_argument("--version", action="version", version=f"rag-eval-gate {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("score", help="score a run against a dataset")
    s.add_argument("--dataset", "-d", required=True)
    s.add_argument("--run", "-r", required=True)
    s.add_argument("--metrics", "-m", help="comma-separated metric names (default: all)")
    s.add_argument("--out", "-o", required=True)
    s.set_defaults(func=cmd_score)

    b = sub.add_parser("baseline", help="manage baselines")
    bsub = b.add_subparsers(dest="bcmd", required=True)
    pr = bsub.add_parser("promote", help="promote a scores file to a baseline")
    pr.add_argument("scores")
    pr.add_argument("--out", "-o", required=True)
    pr.add_argument("--note", help="free-text note stored in the baseline")
    pr.set_defaults(func=cmd_promote)

    c = sub.add_parser("compare", help="compare a scores file with a baseline")
    c.add_argument("--baseline", "-b", required=True)
    c.add_argument("--scores", "-s", required=True)
    _report_args(c)
    c.set_defaults(func=cmd_compare)

    g = sub.add_parser("gate", help="score a run and compare it with a baseline in one step")
    g.add_argument("--dataset", "-d", required=True)
    g.add_argument("--run", "-r", required=True)
    g.add_argument("--baseline", "-b", required=True)
    g.add_argument("--scores-out", help="also save the fresh scores")
    _report_args(g)
    g.set_defaults(func=cmd_gate)

    sub.add_parser("list-metrics", help="show the metric catalogue").set_defaults(func=cmd_list)
    sub.add_parser("setup", help="download NLTK data used by continuous-eval (one-time, needs network)").set_defaults(func=cmd_setup)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return 0 if e.code == 0 else 2
    try:
        return int(args.func(args))
    except RegError as e:
        Console(stderr=True).print(f"[red]error:[/] {e}")
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
