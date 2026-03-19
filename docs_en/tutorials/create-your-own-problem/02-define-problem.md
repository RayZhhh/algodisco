# Defining Your Problem

Before creating an evaluator, you need to clearly define your problem. This guide will help you formalize your algorithm design task.

## Problem Types

algodisco can help with various types of algorithm design problems:

### 1. Optimization Problems

Find an algorithm that minimizes or maximizes a metric.

**Example**: Online Bin Packing
- Goal: Minimize the number of bins used
- Input: Items with different sizes, bin capacity
- Output: Priority function for bin selection

### 2. Classification Problems

Design a classifier or decision function.

**Example**: Sorting
- Goal: Correctly sort arrays of various sizes
- Input: An unsorted array
- Output: Sorting algorithm

### 3. Heuristic Design

Create heuristics for combinatorial problems.

**Example**: Admissible Set
- Goal: Maximize the size of an admissible set
- Input: Vector constraints
- Output: Priority function for selecting vectors

## Formalizing Your Problem

Answer these questions to formalize your problem:

### 1. What is the input?

What does the algorithm receive as input? Define the data types and structures.

### 2. What is the output?

What should the algorithm return? A value, a function, a classification?

### 3. How do you measure success?

What metric determines if one algorithm is better than another?

- **Accuracy**: Fraction of correct outputs
- **Speed**: Execution time
- **Quality**: Solution quality (e.g., bins used, set size)
- **Custom**: Domain-specific metric

### 4. What is the search space?

What aspects of the algorithm can vary?

- Algorithm logic
- Parameter values
- Heuristic functions
- Decision boundaries

## Example: Maximum Value Problem

Let's formalize the "find maximum value" problem:

| Aspect | Definition |
|--------|------------|
| Input | List of integers |
| Output | Maximum integer value |
| Success Metric | Fraction of test cases passed |
| Search Space | Implementation of the solve() function |

### Test Cases

```python
test_cases = [
    {"input": [1, 2, 3], "expected": 3},
    {"input": [3, 2, 1], "expected": 3},
    {"input": [], "expected": 0},  # Edge case
    {"input": [-1, -5, -2], "expected": -1},
]
```

## Exercise

Define your own problem by filling in this template:

```
Problem Name: _______________

Input:
- _______________

Output:
- _______________

Success Metric:
- _______________

Search Space:
- _______________
```

In the next section, we'll learn how to create an evaluator based on your problem definition.
