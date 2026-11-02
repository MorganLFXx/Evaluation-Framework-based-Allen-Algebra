"""User-facing entry points for the `run` and `init` subcommands."""

from __future__ import annotations

import os
from typing import Optional

import yaml
from pydantic import ValidationError
from rich.console import Console
from rich.prompt import Confirm, IntPrompt, Prompt

from . import paths
from .config import ExperimentConfig
from .orchestrator import resolve_stages, run_experiment

console = Console()


def _load_config(path: str) -> ExperimentConfig:
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"invalid YAML in {path}:\n{e}") from e
    if raw is None:
        raise ValueError(f"config file {path} is empty")
    if not isinstance(raw, dict):
        raise ValueError(f"config file {path} must contain a mapping at the top level")
    return ExperimentConfig.model_validate(raw)


def _report_validation_error(e: ValidationError) -> None:
    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"]) or "(root)"
        console.print(f"  - {loc}: {err['msg']}")


def main_run(args) -> int:
    try:
        cfg = _load_config(args.config)
    except ValidationError as e:
        console.print(f"[bold red]Invalid config {args.config}:[/bold red]")
        _report_validation_error(e)
        return 1
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return 1

    stages = resolve_stages(cfg, args.stage)

    if args.dry_run:
        stem = paths.dataset_stem(cfg.name, cfg.task, cfg.dataset)
        if cfg.dataset:
            dataset_file = f"{paths.DATASETS_DIR}/{stem}.json"
            jsonl_file = f"{paths.DATASETS_DIR}/{stem}.jsonl"
            if not os.path.exists(dataset_file) and os.path.exists(jsonl_file):
                dataset_file = jsonl_file
        else:
            dataset_file = paths.dataset_path(cfg.name, cfg.task)
        console.print(f"[bold]Dry run[/bold] for {cfg.name} (task={cfg.task})")
        console.print("  stages:", ", ".join(stages))
        console.print(f"  dataset : {dataset_file}")
        if cfg.model:
            console.print(f"  answers : {paths.answers_path_for(stem, cfg.model)}")
        if "error_check" in stages:
            console.print(f"  explain : {paths.explain_path_for(stem, cfg.model)}")
        return 0

    run_experiment(cfg, force=args.force, only=args.stage)
    return 0


def main_init(args) -> int:
    console.print("[bold]Create a new experiment config[/bold]\n")

    name = args.name or Prompt.ask("Experiment name", default="demo")
    # `auto` is only meaningful together with an explicit `dataset:`, which the
    # wizard does not ask for; the benchmark configs cover that case instead.
    task = args.task or Prompt.ask(
        "Task", choices=["single", "conflict", "fill"], default="single"
    )
    n = args.n if args.n is not None else IntPrompt.ask("Number of samples", default=100)
    depth = args.depth if args.depth is not None else IntPrompt.ask("Depth", default=1)
    model = args.model or Prompt.ask("Response model", default="deepseek-v3.2")
    check_model = args.check_model or Prompt.ask("Check model", default="qwen3.5-plus")
    workers = args.workers if args.workers is not None else IntPrompt.ask("Workers", default=4)

    default_stages = "generate,respond,verify"
    stages_raw = args.stages or Prompt.ask("Stages (comma-separated)", default=default_stages)
    stages = [s.strip() for s in stages_raw.split(",") if s.strip()]

    try:
        cfg = ExperimentConfig(
            name=name,
            task=task,
            n=n,
            depth=depth,
            model=model,
            check_model=check_model,
            workers=workers,
            stages=stages,
        )
    except ValidationError as e:
        console.print("[bold red]Invalid experiment options:[/bold red]")
        _report_validation_error(e)
        return 1

    out_path = args.output or f"{name}.yaml"
    _dump_yaml(cfg, out_path)
    console.print(f"\nWrote config to [bold]{out_path}[/bold]")

    if args.no_run:
        return 0

    if Confirm.ask("Run it now?", default=True):
        # `init` has no --force / --stage flags; auto-run uses the defaults.
        return main_run(_RunArgs(config=out_path, force=False, dry_run=False, stage=None))
    console.print(f"Run later with: [bold]python main.py run {out_path}[/bold]")
    return 0


def _dump_yaml(cfg: ExperimentConfig, out_path: str) -> None:
    data = {
        "name": cfg.name,
        "task": cfg.task,
        "n": cfg.n,
        "depth": cfg.depth,
        "model": cfg.model,
        "check_model": cfg.check_model,
        "workers": cfg.workers,
        "stages": cfg.stages,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)


class _RunArgs:
    """Minimal namespace mirroring the `run` subcommand's argparse result."""

    def __init__(self, config: str, force: bool, dry_run: bool, stage: Optional[str]):
        self.config = config
        self.force = force
        self.dry_run = dry_run
        self.stage = stage
