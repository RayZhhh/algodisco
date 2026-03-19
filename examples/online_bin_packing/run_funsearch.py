#!/usr/bin/env python
"""
Run Online Bin Packing with FunSearch using Python code.

This example demonstrates how to use algodisco directly in Python code
without needing a YAML configuration file.

Usage:
    python examples/online_bin_packing/run_funsearch.py

Set your API key via environment variable:
    export OPENAI_API_KEY="your-api-key"
"""

import os
from algodisco.providers.llm import OpenAIAPI
from algodisco.methods.funsearch.config import FunSearchConfig
from algodisco.methods.funsearch.search import FunSearch
from examples.online_bin_packing.evaluator import OnlineBinPackingEvaluator


# Template algorithm
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
    # Example: First-Fit - place in first bin that can fit
    return bin_capacities
'''

# Task description
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
        logger=None,  # Set to a logger if needed
    )

    print("Starting FunSearch...")
    print(f"  Model: {llm.model}")
    print(f"  Max samples: {config.max_samples}")
    print(f"  Islands: {config.db_num_islands}")
    print()

    search.run()

    print("\nFunSearch completed!")
    print(f"Best score: {search.best_score}")
    print(f"Best program:\n{search.best_program[:500]}...")


if __name__ == "__main__":
    main()
