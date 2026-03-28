# Running with Python Code

This guide shows how to run AlgoDisco directly in Python without YAML.

## Why Use Python?

- Easier debugging
- Programmatic control over configuration
- Simpler integration with your own codebase

## Basic Example

```python
import os

from algodisco.methods.funsearch.config import FunSearchConfig
from algodisco.methods.funsearch.search import FunSearch
from algodisco.providers.llm.openai_api import OpenAIAPI
from my_evaluator import MyEvaluator

TEMPLATE = """from typing import List

def solve(arr: List[int]) -> int:
    \"\"\"Find the maximum value in the array.\"\"\"
    return arr[0] if arr else 0
"""

TASK = """
Implement solve(arr) so that it returns the maximum value in the list.
"""


def main():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Please set OPENAI_API_KEY")

    llm = OpenAIAPI(
        model="gpt-4o-mini",
        api_key=api_key,
        base_url="https://api.openai.com/v1",
    )

    evaluator = MyEvaluator()

    config = FunSearchConfig(
        template_program=TEMPLATE,
        task_description=TASK,
        language="python",
        num_samplers=2,
        num_evaluators=2,
        max_samples=100,
        db_num_islands=5,
    )

    search = FunSearch(
        config=config,
        llm=llm,
        evaluator=evaluator,
        logger=None,
    )
    search.run()


if __name__ == "__main__":
    main()
```

## Bundled Working Example

The repository includes a runnable Python example:

```bash
export OPENAI_API_KEY="your-api-key"
python examples/online_bin_packing/run_funsearch.py
```

That script shows the same pieces wired together:

- `FunSearchConfig`
- `OpenAIAPI`
- `OnlineBinPackingEvaluator`
- `FunSearch`

## Using Other Methods

You can swap the search class and config while keeping the same evaluator and LLM.

### OpenEvolve

```python
from algodisco.methods.openevolve.config import OpenEvolveConfig
from algodisco.methods.openevolve.search import OpenEvolve

config = OpenEvolveConfig(
    template_program=TEMPLATE,
    task_description=TASK,
    language="python",
    max_samples=100,
)

search = OpenEvolve(config=config, llm=llm, evaluator=evaluator)
search.run()
```

### (1+1)-EPS

```python
from algodisco.methods.one_plus_one_eps.config import OnePlusOneEPSConfig
from algodisco.methods.one_plus_one_eps.search import OnePlusOneEPS

config = OnePlusOneEPSConfig(
    template_program=TEMPLATE,
    task_description=TASK,
    language="python",
    max_samples=100,
)

search = OnePlusOneEPS(config=config, llm=llm, evaluator=evaluator)
search.run()
```

## Adding a Logger

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

## When to Use YAML vs Python

| Style | Best For |
|-------|----------|
| YAML | Reproducible experiments and shared configs |
| Python | Quick experiments, debugging, integration work |

## Next Steps

Read [tips and tricks](./08-tips-and-tricks.md) for common pitfalls.
