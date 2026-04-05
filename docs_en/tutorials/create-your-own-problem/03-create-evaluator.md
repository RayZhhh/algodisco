# Creating an Evaluator

The evaluator is the core component that measures how well a generated algorithm performs. This guide shows you how to create one.

## The Evaluator Interface

Your evaluator must inherit from the base `Evaluator` class and implement the `evaluate_program` method:

```python
from algodisco.base.evaluator import Evaluator, EvalResult


class MyEvaluator(Evaluator):
    def evaluate_program(self, program_str: str) -> EvalResult:
        # Your evaluation logic here
        return {"score": 0.5}
```

## Return Value

The evaluator must return a dictionary with at least a `score` key:

```python
{"score": float_value}
```

### Score Semantics

- **Higher is always better**
- Can be any numeric value (negative allowed)
- For **minimization problems**: return negative of your metric

**Example**: If you want to minimize bins used:
```python
score = -mean_bins  # Negative because search maximizes
```

### Optional Fields

You can also return additional information:

```python
{
    "score": 0.8,
    "execution_time": 0.05,      # Optional: execution time in seconds
    "error_msg": None             # Optional: error message if failed
}
```

## Step-by-Step Example: MaxValueEvaluator

Here's a complete evaluator for the "find maximum value" problem:

```python
import os
from typing import List
from algodisco.base.evaluator import Evaluator, EvalResult


class MaxValueEvaluator(Evaluator):
    def __init__(self):
        # Define your test cases
        self.test_cases = [
            {"input": [1, 2, 3], "expected": 3},
            {"input": [3, 2, 1], "expected": 3},
            {"input": [1], "expected": 1},
            {"input": [], "expected": 0},
            {"input": [-1, -5, -2], "expected": -1},
            {"input": list(range(100)), "expected": 99},
        ]

    def evaluate_program(self, program_str: str) -> EvalResult:
        try:
            # Step 1: Compile and execute the generated code
            code = compile(program_str, "<string>", "exec")
            local_ns = {}
            exec(code, {}, local_ns)

            # Step 2: Check if the required function exists
            if "solve" not in local_ns:
                return {"score": 0, "error_msg": "solve function not found"}

            solve_fn = local_ns["solve"]

            # Step 3: Run test cases
            correct = 0
            for tc in self.test_cases:
                result = solve_fn(tc["input"])
                if result == tc["expected"]:
                    correct += 1

            # Step 4: Calculate score
            score = correct / len(self.test_cases)
            return {"score": score}

        except Exception as e:
            return {"score": 0, "error_msg": str(e)}
```

## Using the Sandbox

For safety, wrap your evaluation in the `sandbox_run` decorator:

```python
from algodisco.toolkit.decorators import sandbox_run


class MyEvaluator(Evaluator):
    @sandbox_run(timeout=30, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str) -> EvalResult:
        # Your code here
        g = {}
        exec(program_str, g)
        # ...
```

Parameters:
- `timeout`: Maximum execution time in seconds
- `redirect_to_devnull`: Suppress stdout/stderr

## Complete Example: Online Bin Packing

Here's a more complex evaluator:

```python
import os
import pickle
import numpy as np
from algodisco.base.evaluator import Evaluator, EvalResult
from algodisco.toolkit.decorators import sandbox_run


class OnlineBinPackingEvaluator(Evaluator[EvalResult]):
    def __init__(self, capacity=100, num_items=5000):
        super().__init__()
        self.capacity = capacity
        self.num_items = num_items
        self.instances = self._load_instances()

    def _load_instances(self):
        """Load test instances from dataset."""
        with open("weibull_train.pkl", "rb") as f:
            data = pickle.load(f)
            return data["weibull_5k_train"]

    @sandbox_run(timeout=30, redirect_to_devnull=True)
    def evaluate_program(self, program_str: str) -> EvalResult:
        # Execute generated code to get priority function
        g = {}
        exec(program_str, g)
        priority_func = g["priority"]

        num_bins_list = []

        # Evaluate on test instances
        for name, instance in self.instances.items():
            capacity = instance["capacity"]
            items = tuple(instance["items"])
            bins = np.array([capacity for _ in range(instance["num_items"])])

            # Run the bin packing algorithm
            _, bins_packed = online_binpack(items, bins, priority_func)

            # Count bins used
            num_bins_list.append((bins_packed != capacity).sum())

        mean_bins = np.mean(num_bins_list)
        score = -mean_bins  # Negative because we minimize

        return {"score": score}
```

## Key Points Summary

| Point | Description |
|-------|-------------|
| Return `score` | Must be float, higher is better |
| Minimization | Return negative of your metric |
| Error handling | Return `{"score": 0, "error_msg": str(e)}` |
| Sandbox | Use `@sandbox_run` for safety |
| Test data | Load in `__init__`, evaluate in `evaluate_program` |

## Next Steps

Now that you understand evaluators, let's learn how to [create a template](./04-create-template.md) for the LLM.
