"""Thin wrappers over the execution modules (one per pipeline stage).

Each function lazily imports its execution module inside the body so that
`run --dry-run` and config validation never pull in torch / transformers / API
clients. The wrappers delegate unchanged to the existing entry points and only
add the path resolution (via runner.paths) and idempotent-skip logic.
"""

from __future__ import annotations

import json
import os

from . import paths
from .config import ExperimentConfig


def _stem(cfg: ExperimentConfig) -> str:
    return paths.dataset_stem(cfg.name, cfg.task, cfg.dataset)


def _dataset_file(stem: str) -> str | None:
    """Return the existing .json/.jsonl file for a dataset stem."""
    for ext in (".json", ".jsonl"):
        path = os.path.join(paths.DATASETS_DIR, f"{stem}{ext}")
        if os.path.exists(path):
            return path
    return None


def _first_jsonl_row(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                return json.loads(line)
    raise ValueError(f"dataset {path} is empty")


def stage_generate(cfg: ExperimentConfig, force: bool = False) -> bool:
    """Generate the dataset (and task variant) if not already present.

    Returns True if generation ran, False if skipped (already exists).
    """
    stem = _stem(cfg)
    if cfg.dataset:
        # An explicitly named dataset is an input artifact (e.g. a released
        # benchmark); the runner must never try to synthesise it.
        existing = _dataset_file(stem)
        if existing is None:
            raise FileNotFoundError(
                f"dataset '{stem}' not found under {paths.DATASETS_DIR}/ "
                "(the `dataset:` field must reference an existing file)"
            )
        if force:
            raise ValueError(
                f"--force cannot regenerate external dataset '{stem}'; "
                "remove `dataset:` from the config to generate a new dataset"
            )
        print(f"  [skip] external dataset: {existing}")
        return False

    target = paths.dataset_path(cfg.name, cfg.task)
    if os.path.exists(target) and not force:
        print(f"  [skip] dataset already exists: {target}")
        return False

    from generate import generate_data
    from generate import generate_sp_task

    generate_data.main(n=cfg.n, name=cfg.name, depth=cfg.depth, hint="indirect pos")
    if cfg.task == "conflict":
        generate_sp_task.generate_conflict_task(cfg.name)
    elif cfg.task == "fill":
        generate_sp_task.generate_fillblank_task(cfg.name)
    return True


def stage_respond(cfg: ExperimentConfig) -> None:
    from generate import generate_response

    stem = _stem(cfg)
    dataset_file = _dataset_file(stem)
    if dataset_file is None:
        raise FileNotFoundError(
            f"dataset '{stem}' not found; run the generate stage first"
        )

    if dataset_file.endswith(".json"):
        generate_response.main(
            name=stem,
            chat_type=cfg.task,
            model=cfg.model,
            workers=cfg.workers,
            hint="hint",
        )
        return

    first = _first_jsonl_row(dataset_file)
    if "target" not in first or "hints" not in first:
        raise ValueError(
            f"unsupported jsonl schema in {dataset_file}: each line must be an "
            "internal-schema sample (target + hints), like final_all.jsonl"
        )

    # Internal-schema jsonl (final_all.jsonl is final_all.json in jsonl form):
    # materialise it next to the .json datasets so the standard response
    # workflow can consume it.
    with open(dataset_file, "r", encoding="utf-8") as f:
        samples = [json.loads(line) for line in f if line.strip()]
    json_path = os.path.join(paths.DATASETS_DIR, f"{stem}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(samples, f, indent=4, ensure_ascii=False)
    generate_response.main(
        name=stem,
        chat_type=cfg.task,
        model=cfg.model,
        workers=cfg.workers,
        hint="hint",
    )


def stage_verify(cfg: ExperimentConfig) -> int:
    """Verify answers in place; returns the number of correct samples."""
    from explain import qa_checker

    return qa_checker.answer_verify(paths.answers_key_for(_stem(cfg), cfg.model))


def stage_error_check(cfg: ExperimentConfig) -> None:
    from explain import error_checker

    stem = _stem(cfg)
    answers_stem = paths.answers_key_for(stem, cfg.model)
    answers_path = paths.answers_path_for(stem, cfg.model)
    with open(answers_path, "r", encoding="utf-8") as f:
        samples = json.load(f)
    if not samples or "paths" not in samples[0] or "hints" not in samples[0]:
        print(
            "  [skip] error_check needs internal hints/paths; "
            "this dataset only supports respond + verify"
        )
        return

    error_checker.main(
        path=answers_stem,
        workers=cfg.workers,
        model=cfg.check_model,
    )
