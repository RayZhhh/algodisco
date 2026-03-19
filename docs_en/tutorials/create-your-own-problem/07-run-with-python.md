# Running with Python Code

This guide shows how to run algorithmic directly in Python code without YAML configuration.

## Why Use Python Style?

- **Easier debugging**: Direct control over the code
- **Flexible**: Programmatic configuration
- **Quick iteration**: No need to edit YAML files

## Basic Example

Here's how to run FunSearch directly in Python:

```python
import os
from algodisco.providers.llm import OpenAIAPI
from algodisco.methods.funsearch.config import FunSearchConfig
from algodisco.methods.funsearch.search import FunSearch
from my_evaluator import MyEvaluator

# Your template
TEMPLATE = '''from typing import List

def solve(arr: List[int]) -> int:
    """Find the maximum value in the array."""
    # TODO: Implement this function
    return arr[0] if arr else 0
'''

# Your task description
TASK = '''
Implement the solve function to find the maximum value in an array.
'''


def main():
    # Set up API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Create LLM provider
    llm = OpenAIAPI(
        model="gpt-4o-mini",
        api_key=api_key,
    )

    # Create evaluator
    evaluator = MyEvaluator()

    # Configure FunSearch
    config = FunSearchConfig(
        template_program=TEMPLATE,
        task_description=TASK,
        language="python",
        num_samplers=2,
        num_evaluators=2,
        max_samples=100,
        db_num_islands=5,
    )

    # Create and run search
    search = FunSearch(
        config=config,
        llm=llm,
        evaluator=evaluator,
        logger=None,  # Or add a logger
    )

    search.run()

    print(f"Best score: {search.best_score}")


if __name__ == "__main__":
    main()
```

## Complete Working Example

Here's the full code from `examples/online_bin_packing/run_funsearch.py`:

```python
import os
from algodisco.providers.llm import OpenAIAPI
from algodisco.methods.funsearch.config import FunSearchConfig
from algodisco.methods.funsearch.search import FunSearch
from examples.online_bin_packing.evaluator import OnlineBinPackingEvaluator

TEMPLATE_PROGRAM = '''from typing import List

def priority(item: float, bin_capacities: List[float]) -> List[float]:
    """
    Calculate priority for placing an item into each bin.

    Args:
        item: The item size to be placed.
        bin_capacities: Available capacity of each bin.

    Returns:
        A list of priority scores (higher is better).
    """
    # TODO: Implement your algorithm here
    return bin_capacities
'''

TASK_DESCRIPTION = '''
Implement a priority function for the online bin packing problem.
Given an item size and available bin capacities, assign a priority score
to each bin. The item will be placed in the bin with the highest priority.
Goal: Minimize the number of bins used.
'''


def main():
    # Set up API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: Please set OPENAI_API_KEY environment variable")
        print("  export OPENAI_API_KEY='your-openai-key'")
        return

    # Create LLM provider
    llm = OpenAIAPI(
        model="gpt-4o-mini",
        api_key=api_key,
    )

    # Create evaluator
    evaluator = OnlineBinPackingEvaluator()

    # Configure FunSearch
    config = FunSearchConfig(
        template_program=TEMPLATE_PROGRAM,
        task_description=TASK_DESCRIPTION,
        language="python",
        num_samplers=2,
        num_evaluators=2,
        examples_per_prompt=2,
        samples_per_prompt=2,
        max_samples=100,
        llm_max_tokens=1024,
        llm_timeout_seconds=120,
        db_num_islands=5,
    )

    # Create and run FunSearch
    search = FunSearch(
        config=config,
        llm=llm,
        evaluator=evaluator,
        logger=None,
    )

    print("Starting FunSearch...")
    search.run()
    print(f"\nBest score: {search.best_score}")


if __name__ == "__main__":
    main()
```

## Running the Example

```bash
export OPENAI_API_KEY="your-api-key"
python examples/online_bin_packing/run_funsearch.py
```

## Using Other Methods

### OpenEvolve

```python
from algodisco.methods.openevolve.config import OpenEvolveConfig
from algodisco.methods.openevolve.search import OpenEvolve

config = OpenEvolveConfig(
    template_program=TEMPLATE,
    task_description=TASK,
    num_samplers=2,
    max_samples=100,
)

search = OpenEvolve(
    config=config,
    llm=llm,
    evaluator=evaluator,
)
search.run()
```

### (1+1)-EPS

```python
from algodisco.methods.one_plus_one_eps.config import OnePlusOneEPSConfig
from algodisco.methods.one_plus_one_eps.search import OnePlusOneEPS

config = OnePlusOneEPSConfig(
    template_program=TEMPLATE,
    task_description=TASK,
    max_samples=100,
)

search = OnePlusOneEPS(
    config=config,
    llm=llm,
    evaluator=evaluator,
)
search.run()
```

## Adding Logging

```python
from algodisco.providers.logger.pickle_logger import BasePickleLogger

logger = BasePickleLogger(logdir="logs/my_experiment")

search = FunSearch(
    config=config,
    llm=llm,
    evaluator=evaluator,
    logger=logger,
)
```

## When to Use What?

| Style | Best For |
|-------|----------|
| YAML | Production, reproducibility |
| Python | Quick experiments, debugging |

## Next Steps

Check out [tips and tricks](./08-tips-and-tricks.md) for common pitfalls.
