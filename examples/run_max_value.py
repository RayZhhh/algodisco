#!/usr/bin/env python
"""
Simple example: Find maximum value in an array using FunSearch.

This example demonstrates how to use algodisco to discover an algorithm
that finds the maximum value in an array.
"""

import os
import tempfile
from algodisco.providers.llm import OpenAIAPI
from algodisco.base.evaluator import Evaluator, EvalResult


# Define the evaluator
class MaxValueEvaluator(Evaluator):
    def __init__(self):
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
            # Compile and execute
            code = compile(program_str, "<string>", "exec")
            local_ns = {}
            exec(code, {}, local_ns)

            if "solve" not in local_ns:
                return {"score": 0, "error_msg": "solve function not found"}

            solve_fn = local_ns["solve"]

            # Run tests
            correct = 0
            for tc in self.test_cases:
                result = solve_fn(tc["input"])
                if result == tc["expected"]:
                    correct += 1

            score = correct / len(self.test_cases)
            return {"score": score}

        except Exception as e:
            return {"score": 0, "error_msg": str(e)}


# Template program
TEMPLATE = '''from typing import List

def solve(arr: List[int]) -> int:
    """Find the maximum value in the array."""
    # TODO: Implement this function
    return arr[0] if arr else 0
'''

# Task description
TASK_DESCRIPTION = '''
Implement the `solve(arr: List[int]) -> int` function to find the maximum value in the given array.
'''


def main():
    # Set up API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Please set OPENAI_API_KEY environment variable")
        return

    # Create LLM
    llm = OpenAIAPI(
        model="gpt-4o-mini",
        api_key=api_key
    )

    # Create evaluator
    evaluator = MaxValueEvaluator()

    # Test the evaluator with template
    print("Testing template...")
    result = evaluator.evaluate_program(TEMPLATE)
    print(f"Template score: {result}")

    # Test with a correct implementation
    correct_code = '''
from typing import List

def solve(arr: List[int]) -> int:
    if not arr:
        return 0
    max_val = arr[0]
    for x in arr:
        if x > max_val:
            max_val = x
    return max_val
'''

    print("\nTesting correct implementation...")
    result = evaluator.evaluate_program(correct_code)
    print(f"Correct score: {result}")


if __name__ == "__main__":
    main()
