# Introduction

Welcome to the AlgoDisco tutorial for creating your own problem.

## What Is AlgoDisco?

AlgoDisco is a framework for **LLM-driven automated algorithm design**. It uses large language models to generate, evaluate, and improve algorithm candidates through iterative search.

## What Can AlgoDisco Do?

- **Discover new algorithms** from a task description and template
- **Optimize existing heuristics** by searching for stronger implementations
- **Explore a program space** with multiple search strategies such as FunSearch and OpenEvolve

## Prerequisites

Before starting this tutorial, make sure you have:

1. Python 3.11+ installed
2. An API key for the LLM provider you want to use
3. Basic Python familiarity
4. A working local checkout of this repository

If you have not run the bundled example yet, start with [Quick Start](../../getting-started/quickstart.md) first.

## What You Will Build

In this tutorial, you will create the four pieces that AlgoDisco needs:

1. A clear problem definition
2. An evaluator that scores generated programs
3. A template program that defines the editable search space
4. A YAML or Python entry point that runs the search

## Tutorial Path

Follow the sections in this order:

1. [Define your problem](./02-define-problem.md)
2. [Create an evaluator](./03-create-evaluator.md)
3. [Write a template](./04-create-template.md)
4. [Choose a search method](./05-choose-method.md)
5. [Run with YAML](./06-run-with-yaml.md)
6. [Run with Python](./07-run-with-python.md)
7. [Tips and tricks](./08-tips-and-tricks.md)

## Quick Example

Here is the smallest shape of a custom evaluator:

```python
from algodisco.base.evaluator import Evaluator, EvalResult


class MyEvaluator(Evaluator):
    def evaluate_program(self, program_str: str) -> EvalResult:
        score = ...  # Higher is better
        return {"score": score}
```

The next sections fill in the rest of the workflow.
