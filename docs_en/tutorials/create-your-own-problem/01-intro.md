# Introduction

Welcome to the algodisco tutorial for creating your own problem!

## What is algorithmic?

algodisco is a framework for **LLM-driven automated algorithm design**. It uses large language models to discover and optimize algorithms through evolutionary search methods.

## What can algorithmic do?

- **Discover new algorithms**: Given a problem description, algodisco can generate and improve algorithms
- **Optimize existing heuristics**: Improve the performance of heuristic functions
- **Explore algorithm space**: Search through many algorithm variants to find the best one

## Prerequisites

Before starting this tutorial, make sure you have:

1. **Python 3.11+** installed
2. **API key** for an LLM provider (OpenAI, Claude, vLLM, or SGLang)
3. Basic understanding of Python programming

## What you'll learn

In this tutorial, you'll learn how to:

1. [Define your problem](./02-define-problem.md) - Formalize your algorithm design task
2. [Create an evaluator](./03-create-evaluator.md) - Build code to evaluate generated algorithms
3. [Write a template](./04-create-template.md) - Create a code template for the LLM
4. [Choose a search method](./05-choose-method.md) - Select the right search algorithm
5. [Run the search](./06-run-with-yaml.md) - Execute your experiment

## Quick Example

Here's a sneak peek at what you'll create:

```python
from algodisco.base.evaluator import Evaluator, EvalResult


class MyEvaluator(Evaluator):
    def evaluate_program(self, program_str: str) -> EvalResult:
        # Execute and evaluate the generated algorithm
        score = ...  # Higher is better
        return {"score": score}
```

Let's get started!
