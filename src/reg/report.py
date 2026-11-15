"""Console, Markdown and JSON reports."""

from __future__ import annotations

import json

from rich.console import Console
from rich.table import Table

from .compare import FLOOR, NOISE, OK, REGRESSED, Comparison, ItemRegression, MetricResult

LABELS = {OK: "pass", NOISE: "pass (drop within noise)", REGRESSED: "REGRESSED", FLOOR: "BELOW FLOOR"}


def _status(r: MetricResult) -> str:
    label = LABELS[r.status]
    if r.failed and r.severity == "warn":
        label += " (warn)"
    return label


def _allowed(r: MetricResult) -> str:
    parts = []
    if r.margin is not None:
        parts.append(f"-{r.margin:.3f}")
    if r.floor is not None:
        parts.append(f"min {r.floor:.2f}")
    return ", ".join(parts)


def _drops(i: ItemRegression) -> str:
    return ", ".join(f"{m} {b:.2f} → {c:.2f}" for m, (b, c) in i.drops.items())


def _headline(c: Comparison, fail_on_warn: bool) -> str:
    verdict = "PASS" if c.passed(fail_on_warn) else "FAIL"
    bits = [f"{len(c.errors)} failing"]
    if c.warnings:
        bits.append(f"{len(c.warnings)} warning")
    return f"{verdict}: {', '.join(bits)} of {len(c.results)} metrics"


def _subline(c: Comparison) -> str:
    return f"{c.n_items} items, paired bootstrap {c.samples} samples at {c.confidence:.0%}, baseline dataset {c.baseline_sha[:12]}"


def render_markdown(c: Comparison, fail_on_warn: bool = False) -> str:
    icon = "✅" if c.passed(fail_on_warn) else "❌"
    lines = [
        f"## {icon} rag-eval-gate {_headline(c, fail_on_warn)}",
        "",
        _subline(c),
        "",
        "| Metric | Baseline | Current | Δ | 95% CI of Δ | Allowed | Result |".replace("95%", f"{c.confidence:.0%}"),
        "|---|---:|---:|---:|---|---|---|",
    ]
    for r in c.results:
        result = f"**{_status(r)}**" if r.failed else _status(r)
        lines.append(
            f"| `{r.metric}` | {r.baseline:.3f} | {r.current:.3f} | {r.delta:+.3f} | "
            f"[{r.ci_low:+.3f}, {r.ci_high:+.3f}] | {_allowed(r)} | {result} |"
        )
    if c.worst_items:
        lines += ["", "### Items that got worse", "", "| Item | Metrics that dropped (before → after) |", "|---|---|"]
        lines += [f"| `{i.item}` | {_drops(i)} |" for i in c.worst_items]
    lines += ["", "<sub>A metric fails only if its mean drop exceeds the allowed margin *and* the confidence interval excludes zero.</sub>"]
    return "\n".join(lines) + "\n"


def render_json(c: Comparison, fail_on_warn: bool = False) -> str:
    return json.dumps(c.to_dict(fail_on_warn), indent=2) + "\n"


def make_console(stderr: bool = False) -> Console:
    """CI logs are not terminals and default to 80 columns, which wraps tables."""
    probe = Console(stderr=stderr)
    return probe if probe.is_terminal else Console(stderr=stderr, width=132)


def print_console(c: Comparison, fail_on_warn: bool = False, console: Console | None = None) -> None:
    console = console or make_console()
    style = "bold green" if c.passed(fail_on_warn) else "bold red"
    console.print(f"[{style}]rag-eval-gate {_headline(c, fail_on_warn)}[/]")
    console.print(_subline(c), style="dim")
    t = Table(show_edge=False)
    for col, just in [("metric", "left"), ("baseline", "right"), ("current", "right"), ("delta", "right")]:
        t.add_column(col, justify=just)
    t.add_column(f"{c.confidence:.0%} CI")
    t.add_column("allowed")
    t.add_column("result")
    for r in c.results:
        colour = "red" if r.failed and r.severity == "error" else "yellow" if r.failed or r.status == NOISE else "green"
        t.add_row(
            r.metric,
            f"{r.baseline:.3f}",
            f"{r.current:.3f}",
            f"{r.delta:+.3f}",
            f"[{r.ci_low:+.3f}, {r.ci_high:+.3f}]",
            _allowed(r),
            f"[{colour}]{_status(r)}[/]",
        )
    console.print(t)
    if c.worst_items:
        console.print("\nItems that got worse:")
        w = Table(show_edge=False)
        w.add_column("item")
        w.add_column("worst delta", justify="right")
        w.add_column("metrics that dropped")
        for i in c.worst_items:
            w.add_row(i.item, f"{i.worst_delta:+.3f}", ", ".join(i.drops))
        console.print(w)
