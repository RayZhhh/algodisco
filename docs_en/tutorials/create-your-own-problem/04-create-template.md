# Creating a Template Program

The template program is the code skeleton that the LLM will fill in. This guide shows you how to write effective templates.

## What is a Template?

A template is a Python code snippet with:
- Function signature(s) with type hints
- Docstring explaining the task
- Placeholder return value(s)

The LLM generates the implementation body.

## Template Format

### Basic Structure

```python
from typing import List

def solve(input_data):
    """
    Describe what this function should do.

    Args:
        input_data: Description of input

    Returns:
        Description of output
    """
    # TODO: Implement this function
    return placeholder_value
```

## Examples

### Example 1: Simple Function

For the maximum value problem:

```python
from typing import List

def solve(arr: List[int]) -> int:
    """Find the maximum value in the array."""
    # TODO: Implement this function
    return arr[0] if arr else 0
```

### Example 2: Priority Function

For bin packing:

```python
from typing import List

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
```

### Example 3: Multiple Functions

```python
import numpy as np
from typing import Dict, Tuple

def priority(el: Tuple[int, ...], n: int = 15, w: int = 10) -> float:
    """
    Returns the priority with which we want to add `el` to the set.

    Args:
        el: the unique vector
        n: length of the vector
        w: number of non-zero elements

    Returns:
        Priority score (higher is better)
    """
    # TODO: Implement your priority function
    return 0.0
```

## Best Practices

### 1. Use Type Hints

Type hints help the LLM understand expected input/output types:

```python
# Good
def solve(arr: List[int]) -> int:

# Less clear
def solve(arr):
```

### 2. Write Clear Docstrings

Include:
- What the function does
- Description of each parameter
- Description of return value

### 3. Provide Meaningful Defaults

Default values help guide the LLM:

```python
def priority(item: float, bin_capacities: List[float], strategy: str = "first_fit") -> List[float]:
```

### 4. Include Imports

Include all necessary imports at the top:

```python
import math
import numpy as np
from typing import List, Dict
```

### 5. Return Reasonable Defaults

The TODO return value is used when sampling starts:

```python
# For priority functions - return equal priorities
return bin_capacities

# For scalar returns - return 0
return 0

# For classifiers - return most common class
return 0
```

## Common Mistakes

### ❌ Too Vague

```python
def solve(x):
    """Solve the problem."""
    pass
```

### ✅ Clear and Specific

```python
def solve(arr: List[int]) -> int:
    """Find the maximum value in the array.

    Args:
        arr: A list of integers

    Returns:
        The maximum integer value in the array
    """
    return arr[0] if arr else 0
```

## Task Description

Along with the template, you should provide a task description that gives context:

```
Problem: Find the maximum value in an array.

Your task is to implement the `solve` function that takes a list
of integers and returns the maximum value.

Requirements:
- Handle empty arrays (return 0)
- Handle negative numbers
- Must work for arrays of any size
```

## Next Steps

Now let's learn how to [choose a search method](./05-choose-method.md) that's right for your problem.
