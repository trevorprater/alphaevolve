# Marking Code for Evolution

This guide explains how to mark code sections for evolution using AlphaEvolve's evolvable block system.

## Basic Syntax

Mark code sections with special comments to indicate they can be evolved:

```python
# EVOLVABLE_START: block_name
def my_function(x, y):
    result = x + y
    return result * 2
# EVOLVABLE_END
```

## Block Naming

Each evolvable block must have a unique name:

```python
# EVOLVABLE_START: sorting_algorithm
def sort_numbers(numbers):
    return sorted(numbers)
# EVOLVABLE_END

# EVOLVABLE_START: search_function
def find_item(items, target):
    return target in items
# EVOLVABLE_END
```

## Supported Code Types

### Functions

```python
# EVOLVABLE_START: calculate_fibonacci
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
# EVOLVABLE_END
```

### Class Methods

```python
class Calculator:
    # EVOLVABLE_START: multiply_method
    def multiply(self, a, b):
        return a * b
    # EVOLVABLE_END
```

### Code Blocks

```python
def process_data(data):
    # EVOLVABLE_START: data_processing
    processed = []
    for item in data:
        if item > 0:
            processed.append(item * 2)
    return processed
    # EVOLVABLE_END
```

### Mathematical Expressions

```python
# EVOLVABLE_START: distance_formula
def calculate_distance(x1, y1, x2, y2):
    return ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
# EVOLVABLE_END
```

## Best Practices

### Keep Blocks Focused

Mark specific, well-defined functionality rather than large code sections:

```python
# Good: Focused algorithm
# EVOLVABLE_START: binary_search
def binary_search(arr, target):
    left, right = 0, len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1
# EVOLVABLE_END

# Avoid: Too broad
# EVOLVABLE_START: entire_class  # Don't do this
class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add_data(self, item):
        self.data.append(item)
    
    def process(self):
        # ... lots of code
# EVOLVABLE_END
```

### Maintain Interface Consistency

Ensure evolved code maintains the same input/output interface:

```python
# EVOLVABLE_START: optimization_target
def optimize_function(x, y, z):
    # The LLM can change the implementation
    # but must return a single numeric value
    return x * y + z
# EVOLVABLE_END
```

### Avoid External Dependencies

Keep evolvable blocks self-contained when possible:

```python
# Good: Self-contained
# EVOLVABLE_START: string_processor
def process_string(text):
    # Only use built-in functions
    return text.upper().strip()
# EVOLVABLE_END

# Problematic: External dependencies
# EVOLVABLE_START: complex_processor
def process_data(data):
    # Relies on external libraries
    import numpy as np
    import pandas as pd
    return np.array(data).mean()
# EVOLVABLE_END
```

## Multiple Blocks in One File

You can have multiple evolvable blocks in a single file:

```python
# math_functions.py

# EVOLVABLE_START: addition_function
def add_numbers(a, b):
    return a + b
# EVOLVABLE_END

# EVOLVABLE_START: multiplication_function  
def multiply_numbers(a, b):
    return a * b
# EVOLVABLE_END

# EVOLVABLE_START: power_function
def power(base, exponent):
    return base ** exponent
# EVOLVABLE_END

# Non-evolvable helper function
def validate_input(x):
    return isinstance(x, (int, float))
```

## Common Patterns

### Algorithm Implementations

```python
# EVOLVABLE_START: quicksort_algorithm
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
# EVOLVABLE_END
```

### Mathematical Computations

```python
# EVOLVABLE_START: numerical_integration
def integrate(func, a, b, n_steps=1000):
    step_size = (b - a) / n_steps
    result = 0
    for i in range(n_steps):
        x = a + i * step_size
        result += func(x) * step_size
    return result
# EVOLVABLE_END
```

### Data Transformations

```python
# EVOLVABLE_START: data_normalizer
def normalize_data(data):
    min_val = min(data)
    max_val = max(data)
    if max_val == min_val:
        return [0.5] * len(data)
    return [(x - min_val) / (max_val - min_val) for x in data]
# EVOLVABLE_END
```

## Troubleshooting

### Block Not Found

If AlphaEvolve can't find your evolvable blocks:

1. Check comment syntax (exact spelling: `EVOLVABLE_START` and `EVOLVABLE_END`)
2. Ensure block names are unique
3. Verify file is in the correct location
4. Check for proper indentation

### Syntax Errors

Common issues:

```python
# Wrong: Missing colon
# EVOLVABLE_START block_name

# Wrong: Typo in comment
# EVOLVABEL_START: block_name

# Wrong: Missing block name
# EVOLVABLE_START:

# Correct
# EVOLVABLE_START: block_name
def my_function():
    pass
# EVOLVABLE_END
```

### Evolution Fails

If evolution produces broken code:

1. Simplify the evolvable block
2. Add more constraints in your evaluation function
3. Provide better examples in your task description
4. Use more specific prompts for the LLM

## Next Steps

- [Write effective evaluation functions](evaluation-functions.md)
- [Configure evolution parameters](running-evolution.md)
- [See complete examples](../examples/basic-optimization.md)