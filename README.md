# ALTER: An Allen’s Algebra-Based Evaluation Framework for Temporal Reasoning of LLMs

## Overview
Temporal reasoning is a core capability for large language models (LLMs) to understand and reason about real-world event sequences. Existing synthetic temporal reasoning benchmarks suffer from **information leakage** or only assess explicit temporal relations, lacking rigorous evaluation of **implicit multi-event temporal reasoning** under complex scenarios.

To address these limitations, we propose **ALTER**, a formally grounded, scalable evaluation framework built on **Allen’s Interval Algebra**. ALTER constructs complex temporal networks via compositional rules of Allen’s 13 basic interval relations, then converts these formal structures into natural language. We validate and release a **2,500 QA benchmark** covering three core tasks and five reasoning depths, enabling systematic evaluation of LLMs’ temporal reasoning abilities.

### Three Evaluation Tasks
- **Goal-Oriented Deduction (GOD)**: Infer the implicit temporal relation between two target events via multi-hop reasoning.
- **Local Gap Completion (LGC)**: Hypothesize valid temporal sequences for missing implicit relations without explicit constraints.
- **Contradiction Source Detection (CSD)**: Identify hidden temporal contradictions in complex event networks.

## Environment Setup
### System Requirements
- Python ≥ 3.10
- GPU (optional, ≥24GB VRAM recommended for local 7B+ model deployment)
- LLM API keys 

### Install Dependencies
```bash
pip install -r requirements.txt
```

### API Configuration
Create a `.env` file in the root directory and fill in your API keys:
```env
# Closed-source Models
DEEPSEEK_API_KEY=your_api_key
QWEN_API_KEY=your_api_key
SEED_API_KEY=your_api_key
GEMINI_API_KEY=your_api_key

# Open-source Models (optional, for vLLM deployment)
```

## Repository Structure
- datasets/: datasets and answer files
    - final_all.jsonl: A ready-to-use benchmark that does not depend on this repository
    - final_{task}.json: Benchmark compatible with this code repository workflow
- generate/: data generation and prompt construction
- explain/: answer verification and error checking
- probing/: probing training and inference
- utils/: shared utilities

## Quick Start
### Full Pipeline (Generate → Infer → Verify → Analyze)
```bash
python main.py pipeline \
  --name demo_data \
  --n 100 \
  --depth 2 \
  --chat_type single \
  --model deepseek-v3.2 \
  --check-model qwen3.5-plus \
  --workers 4
```

Optional: skip error checking

```bash
python main.py pipeline --name demo_data --skip-error-check
```

### Step 1: Generate Custom Temporal Data
```bash
# GOD Task (Goal-Oriented Deduction)
python main.py data --name demo_god --n 100 --depth 2 --type single

# CSD Task (Contradiction Source Detection)
python main.py data --name demo_csd --n 100 --depth 2 --type conflict

# LGC Task (Local Gap Completion)
python main.py data --name demo_lgc --n 100 --depth 2 --type fill
```
**Arguments**:
- `--name`: Output dataset name (saved to `datasets/`)
- `--n`: Number of samples to generate
- `--depth`: Reasoning depth 
- `--type`: Task type (`single`=GOD, `conflict`=CSD, `fill`=LGC)

### Step 2: LLM Response Generation
```bash
python main.py response \
  --name demo_god \
  --chat_type single \
  --model deepseek-v3.2 \
  --workers 4
```

### Step 3: Answer Verification & Analysis
```bash
# Exact Match (EM) Verification
python main.py qa --mode answer_verify --name demo_god_deepseek-v3.2

# Full Performance Analysis
python main.py qa \
  --mode final_analyze \
  --name demo_god_deepseek-v3.2 \
  --model qwen3.5-plus
```

### Step 4: Error Analysis (NLU vs Reasoning Errors)
```bash
python main.py error \
  --path demo_god \
  --model qwen3.5-plus \
  --workers 4
```
## Notes

See scripts under generate/ and explain/ for detailed parameters and data formats.
