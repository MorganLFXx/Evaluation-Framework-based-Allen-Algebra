"""Declarative experiment configuration (YAML schema + validation).

This module is intentionally dependency-free w.r.t. the rest of the repo
(generate/explain/utils): it only imports pydantic, so config parsing and
validation work without torch / GPU / API keys.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

# Legal stage names, in the order they run.
STAGES = ["generate", "respond", "verify", "error_check"]

TASKS = ["single", "conflict", "fill", "auto"]


class ExperimentConfig(BaseModel):
    """One experiment: one dataset, one task, one response model."""

    name: str = Field(..., description="Experiment / dataset base name.")
    task: str = Field(
        "single",
        description="Task type. single=GOD, conflict=CSD, fill=LGC, auto=per-sample (mixed benchmark).",
    )
    dataset: Optional[str] = Field(
        None,
        description=(
            "Existing dataset stem under datasets/ (e.g. final_single). When set, "
            "generation is skipped and every downstream path is derived from it."
        ),
    )
    n: int = Field(1, ge=0, description="Number of samples to generate.")
    depth: int = Field(1, ge=1, description="Recursion depth for generation.")
    model: Optional[str] = Field(
        None, description="Model for response generation."
    )
    check_model: str = Field(
        "qwen3.5-plus", description="Model for answer verification / error check."
    )
    workers: int = Field(1, ge=1, description="Parallel API workers.")
    stages: List[str] = Field(
        default_factory=lambda: ["generate", "respond", "verify"],
        description="Stages to run, in order.",
    )

    @model_validator(mode="after")
    def _validate(self) -> "ExperimentConfig":
        if self.task not in TASKS:
            raise ValueError(
                f"task must be one of {TASKS}, got '{self.task}'"
            )

        unknown = [s for s in self.stages if s not in STAGES]
        if unknown:
            raise ValueError(
                f"unknown stage(s) {unknown}. Legal stages: {STAGES}"
            )
        # Canonicalise to pipeline order regardless of how the YAML lists them:
        # the stages depend on each other (respond reads generate's output,
        # verify reads respond's output, ...), so a user-declared order such as
        # [verify, respond] must not be honoured as-is.
        self.stages = [s for s in STAGES if s in self.stages]

        if not self.stages:
            raise ValueError("stages must not be empty")

        if self.task == "auto" and not self.dataset:
            raise ValueError("task 'auto' requires an explicit `dataset:` field")

        needs_model = {"respond", "verify", "error_check"} & set(self.stages)
        if needs_model and not self.model:
            raise ValueError(
                f"model is required when stages include {sorted(needs_model)}"
            )

        return self
