"""Single source of truth for dataset / artifact naming conventions.

The execution modules each hardcode these paths independently
(generate_sp_task.py, generate_response.py, qa_checker.py, error_checker.py).
This module centralizes them so the orchestrator derives every path from
(name, task, model) and cannot fall out of sync (the root cause of a past bug
where verify used `name + "_" + model` but error_check used `name`).
"""

from __future__ import annotations

import os

# Dataset directory (relative to repo root).
DATASETS_DIR = "datasets"

# Task name -> filename suffix appended to the base dataset name.
# NOTE: the `fill` task is stored on disk as `_fillblank` (a legacy mismatch
# between the task name and the filename). This is the one place that maps it.
_TASK_SUFFIX = {
    "single": "",
    "conflict": "_conflict",
    "fill": "_fillblank",
}


def task_suffix(task: str) -> str:
    if task not in _TASK_SUFFIX:
        raise ValueError(f"unknown task '{task}'; expected one of {list(_TASK_SUFFIX)}")
    return _TASK_SUFFIX[task]


def dataset_key(name: str, task: str) -> str:
    """On-disk dataset filename stem (without .json)."""
    return f"{name}{task_suffix(task)}"


def dataset_path(name: str, task: str) -> str:
    return os.path.join(DATASETS_DIR, f"{dataset_key(name, task)}.json")


def dataset_stem(name: str, task: str, dataset: str | None = None) -> str:
    """Dataset stem used by every downstream step.

    ``dataset`` explicitly names an existing dataset (e.g. the released
    benchmark ``final_single`` / ``final_conflict`` / ``final_fillblank`` /
    ``final_all``); otherwise the stem is derived from name+task.
    """
    return dataset or dataset_key(name, task)


def answers_key(name: str, task: str, model: str) -> str:
    """Answers file stem (without _with_answers.json)."""
    return f"{dataset_key(name, task)}_{model}"


def answers_key_for(dataset_stem: str, model: str) -> str:
    return f"{dataset_stem}_{model}"


def answers_path_for(dataset_stem: str, model: str) -> str:
    return os.path.join(
        DATASETS_DIR,
        "answers",
        f"{answers_key_for(dataset_stem, model)}_with_answers.json",
    )


def explain_path_for(dataset_stem: str, model: str) -> str:
    return os.path.join(
        DATASETS_DIR,
        "explain",
        f"{answers_key_for(dataset_stem, model)}_with_explanation.json",
    )


def answers_path(name: str, task: str, model: str) -> str:
    return answers_path_for(dataset_key(name, task), model)


def explain_path(name: str, task: str, model: str) -> str:
    return explain_path_for(dataset_key(name, task), model)
