# AlgoDisco Tutorial

Welcome to the AlgoDisco tutorial! This directory contains Jupyter notebooks that will teach you how to use AlgoDisco for algorithm discovery and optimization.

## Tutorial Notebooks

| Notebook | Title | Description |
|----------|-------|-------------|
| 01 | AlgoProto Tutorial | Core data structure for algorithms - detailed API guide |
| 02 | Evaluator Tutorial | How to evaluate algorithm candidates |
| 03 | Sandbox Tutorial | Secure code execution with timeout and resource limits |
| 04 | Parser Tutorial | Code parsing and syntax checking |
| 05 | LLM Provider Tutorial | Using OpenAI, Claude, vLLM, SGLang |
| 06 | Complete Example | Full workflow from config to running search |
| 07 | Python Run Tutorial | Run AlgoDisco directly with Python (no YAML) |

## Learning Path

### Phase 1: Core Concepts
1. **AlgoProto** - Understand the core data structure
2. **Evaluator** - Learn how to evaluate algorithms

### Phase 2: Infrastructure
3. **Sandbox** - Understand secure execution
4. **Parser** - Learn code parsing utilities
5. **LLM Provider** - Configure different LLM backends

### Phase 3: Practice
6. **Complete Example** - Run your first search

## Running AlgoDisco

### Method 1: Using YAML Config (Recommended for quick start)

```bash
# Run funsearch with YAML config
python algodisco/methods/funsearch/main_funsearch.py --config configs/funsearch.yaml

# Run openevolve with YAML config
python algodisco/methods/openevolve/main_openevolve.py --config configs/openevolve.yaml

# Run (1+1)-EPS with YAML config
python algodisco/methods/one_plus_one_eps/main_one_plus_one_eps.py --config configs/one_plus_one_eps.yaml
```

### Method 2: Using Python Script Directly

You can also run AlgoDisco directly from Python code without YAML configuration:

```python
import os

os.environ["OPENAI_API_KEY"] = "your-api-key"

from algodisco.methods.funsearch.config import FunSearchConfig
from algodisco.methods.funsearch.search import FunSearch
from algodisco.providers.llm.openai_api import OpenAIAPI
from your_custom_evaluator import SortingEvaluator

# 1. Create config
config = FunSearchConfig(
    template_program=template_code,  # your template as string
    task_description=task_desc,  # your task description as string
    language="python",
    num_samplers=2,
    num_evaluators=2,
    samples_per_prompt=2,
    max_samples=100,
    llm_max_tokens=1024,
    llm_timeout_seconds=60,
)

# 2. Create LLM provider
llm = OpenAIAPI(
    model="gpt-3.5-turbo",
    api_key=os.environ["OPENAI_API_KEY"],
)

# 3. Create evaluator
evaluator = SortingEvaluator(num_tests=100)

# 4. Run search
search = FunSearch(
    config=config,
    llm=llm,
    evaluator=evaluator,
)
search.run()
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up your API key
export OPENAI_API_KEY="your-api-key"

# Start Jupyter
jupyter notebook
```

## Code Examples

Each notebook contains detailed code examples showing:
- How to use each class and function
- Common patterns and best practices
- Error handling and edge cases

## Additional Resources

- [CLAUDE.md](../CLAUDE.md) - Project overview
- [configs/](../_ignore/configs/) - Example configurations
- [algodisco/methods/](../algodisco/methods/) - Search method implementations
