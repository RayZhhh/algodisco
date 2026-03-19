# Quick Start

This guide will help you run your first algorithm search using algorithmic.

## Overview

The typical workflow consists of:
1. Prepare a template program and task description
2. Configure the search method via YAML
3. Implement an evaluator for your problem
4. Run the search

## Step 1: Prepare Template Program

Create a template Python program that solves your problem. The template should contain:
- Basic structure for solving the problem
- Placeholder functions to be evolved
- A `solve()` function that returns the answer

Example template for finding the maximum value in a list:

```python
from typing import List

def solve(arr: List[int]) -> int:
    """Find the maximum value in the array."""
    # TODO: Implement this function
    return arr[0] if arr else 0
```

## Step 2: Create Task Description

Create a text file describing the task:

```
Implement the `solve(arr: List[int]) -> int` function to find the maximum value in the given array.
The function should handle edge cases like empty arrays.
```

## Step 3: Create Configuration File

Create a YAML configuration file (e.g., `config.yaml`):

```yaml
method:
  template_program_path: "template.py"
  task_description_path: "task.txt"
  language: "python"
  num_samplers: 4
  num_evaluators: 4
  examples_per_prompt: 2
  samples_per_prompt: 4
  max_samples: 100
  llm_max_tokens: 1024
  llm_timeout_seconds: 120
  db_num_islands: 10

llm:
  class_path: "algodisco.providers.llm.openai_api.OpenAIAPI"
  kwargs:
    model: "gpt-3.5-turbo"
    api_key: "your-api-key"

evaluator:
  class_path: "your_evaluator_module.YourEvaluator"
  kwargs: {}

logger:
  class_path: "algodisco.providers.logger.pickle_logger.BasePickleLogger"
  kwargs:
    logdir: "logs/my_search"
```

## Step 4: Implement Evaluator

Create your evaluator class:

```python
from algodisco.base.evaluator import Evaluator, EvalResult


class YourEvaluator(Evaluator):
    def __init__(self):
        self.test_cases = [
            {"input": [1, 2, 3], "expected": 3},
            {"input": [-1, -5, -2], "expected": -1},
            {"input": [0], "expected": 0},
            {"input": [], "expected": 0},
        ]

    def evaluate_program(self, program_str: str) -> EvalResult:
        try:
            # Execute the program in a sandbox
            local_ns = {}
            exec(program_str, {}, local_ns)

            if "solve" not in local_ns:
                return {"score": 0, "error_msg": "solve function not found"}

            solve_fn = local_ns["solve"]

            # Run test cases
            correct = 0
            for tc in self.test_cases:
                result = solve_fn(tc["input"])
                if result == tc["expected"]:
                    correct += 1

            score = correct / len(self.test_cases)
            return {"score": score}

        except Exception as e:
            return {"score": 0, "error_msg": str(e)}
```

## Step 5: Run the Search

Run the search using the appropriate entry point:

```bash
# For FunSearch
python algodisco/methods/funsearch/main_funsearch.py --config config.yaml

# For OpenEvolve
python algodisco/methods/openevolve/main_openevolve.py --config config.yaml

# For (1+1)-EPS
python algodisco/methods/one_plus_one_eps/main_one_plus_one_eps.py --config config.yaml

# For Random Sampling
python algodisco/methods/randsample/main_randsample.py --config config.yaml
```

## Monitoring Results

Results are saved to the log directory specified in your configuration. You can analyze the logs:

```python
import pickle

# Load logged results
with open("logs/my_search/algo.pkl", "rb") as f:
    results = pickle.load(f)

# Find best solution
best = max(results, key=lambda x: x.get("score", 0))
print(f"Best score: {best['score']}")
print(f"Best program:\n{best['program']}")
```

## Next Steps

- [Configuration Guide](configuration.md) - Detailed configuration options
- [Search Methods](../user-guide/search-methods/index.md) - Explore different search algorithms
- [LLM Providers](../user-guide/llm-providers/index.md) - Configure different LLM backends
