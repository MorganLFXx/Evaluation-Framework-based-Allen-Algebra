"""Run an experiment end-to-end with progress reporting and a summary."""

from __future__ import annotations

from typing import Dict, List, Optional

from rich.console import Console
from rich.table import Table

from . import paths
from .config import ExperimentConfig
from .stages import (
    stage_error_check,
    stage_generate,
    stage_respond,
    stage_verify,
)

console = Console()

# Map stage name -> runner callable. Each returns an optional int (verify's
# correct-count) or None. Kept explicit so ordering is the declared order.
_STAGE_RUNNERS = {
    "generate": (lambda cfg, force: stage_generate(cfg, force)),
    "respond": (lambda cfg, force: stage_respond(cfg)),
    "verify": (lambda cfg, force: stage_verify(cfg)),
    "error_check": (lambda cfg, force: stage_error_check(cfg)),
}


def resolve_stages(cfg: ExperimentConfig, only: Optional[str] = None) -> List[str]:
    """Return the ordered list of stages to run for this experiment."""
    stages = cfg.stages
    if only is not None:
        if only not in _STAGE_RUNNERS:
            raise ValueError(f"unknown stage '{only}'; legal stages: {sorted(_STAGE_RUNNERS)}")
        stages = [only]
    return stages


def run_experiment(
    cfg: ExperimentConfig,
    force: bool = False,
    only: Optional[str] = None,
) -> Dict[str, object]:
    """Run the experiment stages in order. Returns per-stage results.

    verify yields an int (correct count), generate yields a bool (ran vs
    skipped), the remaining stages yield None on success.
    """
    results: Dict[str, object] = {}
    stages = resolve_stages(cfg, only)

    console.print(f"[bold]Experiment[/bold] {cfg.name}  task={cfg.task}  model={cfg.model}")

    for stage in stages:
        console.print(f"\n[bold cyan]== Stage: {stage} ==[/bold cyan]")
        with console.status(f"Running {stage}..."):
            results[stage] = _STAGE_RUNNERS[stage](cfg, force)

    _print_summary(cfg, stages, results)
    return results


def _format_result(value: object) -> str:
    if value is None:
        return "done"
    if isinstance(value, bool):
        return "generated" if value else "skipped"
    if isinstance(value, int):
        return f"{value} correct"
    return str(value)


def _print_summary(
    cfg: ExperimentConfig, stages: List[str], results: Dict[str, object]
) -> None:
    table = Table(title="Summary", show_header=True, header_style="bold magenta")
    table.add_column("Stage", style="cyan")
    table.add_column("Result", style="green")

    for stage in stages:
        table.add_row(stage, _format_result(results.get(stage)))

    console.print(table)

    console.print("\n[bold]Artifacts:[/bold]")
    for line in _artifact_lines(cfg, stages):
        console.print(f"  {line}")


def _artifact_lines(cfg: ExperimentConfig, stages: List[str]) -> List[str]:
    stem = paths.dataset_stem(cfg.name, cfg.task, cfg.dataset)
    lines: List[str] = []
    if "generate" in stages or cfg.dataset:
        lines.append(f"dataset: {paths.DATASETS_DIR}/{stem}.json")
    if "respond" in stages or "verify" in stages:
        lines.append(f"answers: {paths.answers_path_for(stem, cfg.model)}")
    if "error_check" in stages:
        lines.append(f"explain: {paths.explain_path_for(stem, cfg.model)}")
    return lines
