# ALTER: An Allen’s Algebra-Based Evaluation Framework for Temporal Reasoning of LLMs

<div align="center">

[![Paper](https://img.shields.io/badge/Paper-NeurIPS%202026%20D%26E%20(Oral)-blue)](https://openreview.net/forum?id=ay0UXDsniW)
[![Dataset](https://img.shields.io/badge/Dataset-Hugging%20Face-yellow)](https://huggingface.co/datasets/xinxiangmg/ALTER)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</div>

> This repository is the official implementation of **ALTER**.
>
> **Paper**: [*ALTER: An Allen's Algebra-Based Evaluation Framework for Temporal Reasoning of LLMs*](https://openreview.net/forum?id=ay0UXDsniW) — **NeurIPS 2026 Track on Evaluations and Datasets (Oral)**
>
> **Authors**: Hongkai Zhou (hkzhou@smail.nju.edu.cn), Yanhui Li (yanhuili@nju.edu.cn) — Nanjing University
>
> **Dataset**: [Hugging Face](https://huggingface.co/datasets/xinxiangmg/ALTER) · **BibTeX**: see [Citation](#citation).

## Overview

Temporal reasoning is a core capability for large language models (LLMs) to understand and reason about real-world event sequences. Existing synthetic temporal reasoning benchmarks suffer from **information leakage** or only assess explicit temporal relations, lacking rigorous evaluation of **implicit multi-event temporal reasoning** under complex scenarios.

To address these limitations, we propose **ALTER**, a formally grounded, scalable evaluation framework built on **Allen’s Interval Algebra**. ALTER constructs complex temporal networks via compositional rules of Allen’s 13 basic interval relations, then converts these formal structures into natural language. We validate and release a **2,500 QA benchmark** covering three core tasks and five reasoning depths (path lengths **1, 10, 20, 40, 60**), enabling systematic evaluation of LLMs’ temporal reasoning abilities. The benchmark contains 1,000 GOD, 1,000 CSD and 500 LGC samples, balanced across the five depths.

### Three Evaluation Tasks

- **Goal-Oriented Deduction (GOD)** — Infer the implicit temporal relation between two target events via multi-hop reasoning.
- **Local Gap Completion (LGC)** — Hypothesize valid temporal sequences for missing implicit relations without explicit constraints.
- **Contradiction Source Detection (CSD)** — Identify hidden temporal contradictions in complex event networks.

## 📊 Benchmark Dataset

The ready-to-use benchmark is released under [`datasets/`](datasets/):

| File                                                             | Task            | Samples | Format                                  |
| ---------------------------------------------------------------- | --------------- | ------- | --------------------------------------- |
| [`datasets/final_single.json`](datasets/final_single.json)       | GOD             | 1,000   | JSON (internal sample schema)           |
| [`datasets/final_conflict.json`](datasets/final_conflict.json)   | CSD             | 1,000   | JSON (internal sample schema)           |
| [`datasets/final_fillblank.json`](datasets/final_fillblank.json) | LGC             | 500     | JSON (internal sample schema)           |
| [`datasets/final_all.jsonl`](datasets/final_all.jsonl)           | GOD + LGC + CSD | 2,500   | JSONL (one internal-schema sample/line) |

- `final_all` is the concatenation of the three task datasets; `final_all.jsonl` is the same 2,500 records serialized as JSONL.
- All four files can be fed directly into the workflow below. If only `final_all.jsonl` is present, the runner materialises `datasets/final_all.json` automatically.
- Each task is balanced over the five reasoning depths (path lengths 1, 10, 20, 40, 60): GOD and CSD have 200 samples per depth, LGC has 100.
- The same benchmark is also hosted on [Hugging Face](https://huggingface.co/datasets/xinxiangmg/ALTER).

## Environment Setup

### System Requirements

- Python ≥ 3.10
- GPU (optional, ≥ 24 GB VRAM recommended for local 7B+ model deployment)
- LLM API keys

### Install Dependencies

```bash
pip install -r requirements.txt
```

### API Configuration

Create a `.env` file in the root directory and fill in your API keys (see `utils/chat.py` for how each is routed by model name):

```env
# DeepSeek (model name starts with "deepseek")
DEEPSEEK_API_KEY=your_api_key

# Tongyi / Qwen (default route, e.g. "qwen3.5-plus")
TONGYI_API_KEY=your_api_key

# Volcano Engine / Doubao-Seed (model name starts with "seed")
VOLCANO_API_KEY=your_api_key

# OpenRouter (Gemini models, called as "google/{model}" via OpenRouter)
OPEN_ROUTE_API_KEY=your_api_key
```

Open-source models (optional) are served via a local vLLM at `http://localhost:18235/v1` and require no API key.

## Repository Structure

- `datasets/` — datasets and answer files
    - `final_{task}.json`: the released benchmark (internal sample schema)
    - `final_all.jsonl`: the three benchmark files concatenated, one sample per line
- `benchmarks/` — runnable YAML configs for the released benchmark files
- `generate/` — data generation and prompt construction
- `explain/` — answer verification and error checking
- `runner/` — experiment orchestration layer (YAML config → run; see below)
- `probing/` — probing training and inference
- `utils/` — shared utilities

## 🏆 Paper Benchmark Evaluation (recommended)

The released benchmark files have dedicated configs under `benchmarks/`. Edit `model` / `check_model` / `workers` in the YAML first, then run:

```bash
# GOD — 1,000 samples
python main.py run benchmarks/final_single.yaml

# CSD — 1,000 samples
python main.py run benchmarks/final_conflict.yaml

# LGC — 500 samples
python main.py run benchmarks/final_fillblank.yaml

# GOD + LGC + CSD — 2,500 samples (task inferred per sample)
python main.py run benchmarks/final_all.yaml
```

These configs use `dataset:` to point at an existing released file instead of generating one. `final_all.yaml` works with either `datasets/final_all.json` or `datasets/final_all.jsonl`; when only the JSONL exists the runner materialises the JSON form automatically. `error_check` runs for all four internal-schema datasets.

Useful flags:

```bash
python main.py run benchmarks/final_single.yaml --dry-run       # validate + print paths
python main.py run benchmarks/final_single.yaml --stage verify  # only one stage
```

Artifacts are named consistently:

```text
datasets/answers/{dataset}_{model}_with_answers.json
datasets/explain/{dataset}_{model}_with_explanation.json
```

## 🚀 Full Pipeline for New Data

### Declarative (YAML)

Describe an experiment in a YAML file and run every stage with one command:

```yaml
# demo_god.yaml
name: demo_god
task: single            # single=GOD, conflict=CSD, fill=LGC
                        # auto=per-sample (only with `dataset:`)
n: 100
depth: 2
model: deepseek-v3.2
check_model: qwen3.5-plus
workers: 4
stages: [generate, respond, verify, error_check]
```

```bash
python main.py init                       # interactive wizard → writes <name>.yaml
python main.py run demo_god.yaml          # generate → respond → verify → error_check
python main.py run demo_god.yaml --dry-run
python main.py run demo_god.yaml --stage verify
python main.py run demo_god.yaml --force  # regenerate the dataset
```

For CSD / LGC, change `task` and `name`:

```yaml
name: demo_csd
task: conflict
```

```yaml
name: demo_lgc
task: fill
```

The runner resolves dataset / answers / explain paths from `(name, task, model)`, so you do not need to remember `_conflict`, `_fillblank`, or `_with_answers.json` suffixes.

### One-shot CLI

```bash
# GOD
python main.py pipeline --name demo_god --n 100 --depth 2 --chat_type single \
  --model deepseek-v3.2 --check-model qwen3.5-plus --workers 4

# CSD
python main.py pipeline --name demo_csd --n 100 --depth 2 --chat_type conflict \
  --model deepseek-v3.2 --check-model qwen3.5-plus --workers 4

# LGC
python main.py pipeline --name demo_lgc --n 100 --depth 2 --chat_type fill \
  --model deepseek-v3.2 --check-model qwen3.5-plus --workers 4
```

Add `--skip-error-check` to stop after answer verification.

## Step-by-Step (manual)

### Naming convention

| Task     | Step 1 writes                                   | Step 2/3 name               | Step 4 `--path`             |
| -------- | ----------------------------------------------- | --------------------------- | --------------------------- |
| GOD      | `datasets/{base}.json`                          | `{base}`                    | `{base}_{model}`            |
| CSD      | `datasets/{base}_conflict.json`                 | `{base}_conflict`           | `{base}_conflict_{model}`   |
| LGC      | `datasets/{base}_fillblank.json`                | `{base}_fillblank`          | `{base}_fillblank_{model}`  |

`{base}` is the `--name` passed to `data`. For CSD/LGC the base dataset is an intermediate artifact; the task dataset carries the suffix.

### Step 1: Generate Custom Temporal Data

```bash
# GOD (Goal-Oriented Deduction)
python main.py data --name demo_god --n 100 --depth 2 --type single

# CSD (Contradiction Source Detection)
python main.py data --name demo_csd --n 100 --depth 2 --type conflict

# LGC (Local Gap Completion)
python main.py data --name demo_lgc --n 100 --depth 2 --type fill
```

### Step 2: LLM Response Generation

```bash
# GOD
python main.py response --name demo_god --chat_type single \
  --model deepseek-v3.2 --workers 4

# CSD
python main.py response --name demo_csd_conflict --chat_type conflict \
  --model deepseek-v3.2 --workers 4

# LGC
python main.py response --name demo_lgc_fillblank --chat_type fill \
  --model deepseek-v3.2 --workers 4
```

### Step 3: Answer Verification

```bash
# GOD
python main.py qa --mode answer_verify --name demo_god_deepseek-v3.2

# CSD
python main.py qa --mode answer_verify --name demo_csd_conflict_deepseek-v3.2

# LGC
python main.py qa --mode answer_verify --name demo_lgc_fillblank_deepseek-v3.2
```

### Step 4: Error Analysis (NLU vs Reasoning)

`--path` is the answers stem (`{dataset}_{model}`), not the dataset file:

```bash
python main.py error --path demo_god_deepseek-v3.2 --model qwen3.5-plus --workers 4
python main.py error --path demo_csd_conflict_deepseek-v3.2 --model qwen3.5-plus --workers 4
python main.py error --path demo_lgc_fillblank_deepseek-v3.2 --model qwen3.5-plus --workers 4
```

### Performance Analysis on the Released Benchmark

After running `response` + `answer_verify` for a released benchmark, `final_analyze` reports per-task, per-depth and per-path-length accuracy:

```bash
python main.py qa --mode final_analyze --name final_single    --model deepseek-v3.2
python main.py qa --mode final_analyze --name final_conflict  --model deepseek-v3.2
python main.py qa --mode final_analyze --name final_fill      --model deepseek-v3.2  # note: final_fill, not final_fillblank
python main.py qa --mode final_analyze --name final_all       --model deepseek-v3.2
```

`final_analyze` only supports the released benchmark names (`final_all`, `final_single`, `final_conflict`, `final_fill`) and the `test_len_*` datasets; custom dataset names are not supported by this mode.

## Citation

<!-- TODO(citation): add the official BibTeX after camera-ready. -->
BibTeX will be added after the camera-ready version.   

## Notes

See scripts under `generate/` and `explain/` for detailed parameters and data formats.

## License

This project is released under the [MIT License](LICENSE).
