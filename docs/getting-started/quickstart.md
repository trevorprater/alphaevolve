# Quick Start Guide

This guide will get you running your first AlphaEvolve experiment in just a few minutes.

## Prerequisites

Before starting, ensure you have:

- [AlphaEvolve installed](installation.md)
- Python 3.12 or higher
- Basic familiarity with Python programming

## Your First Evolution Experiment

Let's evolve a simple mathematical function to demonstrate AlphaEvolve's capabilities.

### Step 1: Create a Test File

Create a Python file with a function to evolve:

```python title="math_optimizer.py"
# EVOLVE-BLOCK-START calculation
def optimize_calculation(x, y, z):
    """
    Calculate a result from three inputs.
    This function will be evolved by AlphaEvolve.
    """
    # Initial implementation - can be improved
    result = x + y + z
    return result
# EVOLVE-BLOCK-END calculation

# Test function for validation
def test_calculation():
    """Simple test to verify our function works."""
    result = optimize_calculation(2, 3, 4)
    print(f"Result: {result}")
    return result

if __name__ == "__main__":
    test_calculation()
```

### Step 2: Create an Evaluation Function

Create an evaluator that measures how well our function performs:

```python title="evaluator.py"
import math

def evaluate(program_code, program_entry):
    """
    Evaluate how well the evolved function performs.
    
    Args:
        program_code: The complete program code
        program_entry: Program entry with metadata
        
    Returns:
        Dictionary with evaluation scores
    """
    try:
        # Execute the program to get the function
        namespace = {}
        exec(program_code, namespace)
        func = namespace.get('optimize_calculation')
        
        if func is None:
            return {"objective": 0.0, "complexity": 10}
        
        # Test the function with various inputs
        test_cases = [
            (1, 2, 3),
            (5, 5, 5),
            (10, 0, -5),
            (-2, 4, 1)
        ]
        
        total_score = 0
        for x, y, z in test_cases:
            try:
                result = func(x, y, z)
                # Reward functions that produce larger results efficiently
                # This is just an example objective
                score = math.log(abs(result) + 1) if result != 0 else 0
                total_score += score
            except Exception:
                # Penalize functions that crash
                total_score -= 1
        
        # Calculate complexity based on code length (simple metric)
        complexity = len(program_code) / 100
        
        return {
            "objective": total_score / len(test_cases),
            "complexity": min(complexity, 10)
        }
        
    except Exception as e:
        # Return poor scores for programs that don't work
        return {"objective": 0.0, "complexity": 10}
```

### Step 3: Set Up Configuration

Initialize your project configuration:

```bash
# Create configuration for mock LLMs (no API keys needed)
alphaevolve setup --template basic

# Or for real LLMs (requires API keys)
alphaevolve setup --template research
```

### Step 4: Run Evolution

Now run your first evolution experiment:

```bash
# Run with interactive monitoring (recommended)
alphaevolve evolve --source math_optimizer.py --evaluator evaluator.py --generations 5 --interactive

# Or run in batch mode
alphaevolve evolve --source math_optimizer.py --evaluator evaluator.py --generations 5
```

You should see output like:

```
Initializing AlphaEvolve components...
✓ Found 1 evolvable block(s)
Starting interactive evolution for 5 generations...

  Best score: 0.850
  Generation 5/5 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:02

Evolution completed!
```

## Understanding the Results

After evolution completes, AlphaEvolve will have:

1. **Explored Variations**: Generated different implementations of your function
2. **Evaluated Performance**: Scored each variant using your evaluation function
3. **Maintained Diversity**: Kept a diverse population using MAP-Elites
4. **Saved Progress**: Stored results and checkpoints for later analysis

### Viewing Results

Check what happened during evolution:

```bash
# List any checkpoints created
alphaevolve checkpoint list

# Analyze the program database (if saved)
alphaevolve analyze --database evolution_storage/databases/program_database_*.json --format table
```

## Exploring Further

Now that you've run your first experiment, try these next steps:

### Experiment with Different Objectives

Modify your evaluation function to optimize for different goals:

```python
# Example: Optimize for mathematical operations
def evaluate(program_code, program_entry):
    # ... test different mathematical properties
    return {
        "accuracy": accuracy_score,
        "efficiency": efficiency_score,
        "complexity": complexity_score
    }
```

### Try Different Code Patterns

Mark different types of code for evolution:

```python
# EVOLVE-BLOCK-START algorithm
def sort_numbers(numbers):
    # Let AlphaEvolve discover sorting algorithms
    return sorted(numbers)
# EVOLVE-BLOCK-END algorithm

# EVOLVE-BLOCK-START optimization
def process_data(data):
    # Optimize data processing logic
    result = []
    for item in data:
        if item > 0:
            result.append(item * 2)
    return result
# EVOLVE-BLOCK-END optimization
```

### Configure for Your Use Case

Edit `alphaevolve.yaml` to customize behavior:

```yaml
# Increase population size for more exploration
evolution:
  population_size: 100
  max_generations: 50

# Use real LLMs for better code generation
llm:
  default_provider: openai
  providers:
    openai:
      model: gpt-4
      api_key: ${OPENAI_API_KEY}
```

## Common Patterns

### Marking Code Blocks

Use descriptive names for evolvable blocks:

```python
# EVOLVE-BLOCK-START data_processing
def process_items(items):
    # Processing logic here
    pass
# EVOLVE-BLOCK-END data_processing

# EVOLVE-BLOCK-START performance_optimization  
def calculate_heavy_computation(data):
    # Expensive computation here
    pass
# EVOLVE-BLOCK-END performance_optimization
```

### Writing Good Evaluators

Create evaluators that guide evolution effectively:

```python
def evaluate(program_code, program_entry):
    """
    Tips for good evaluators:
    1. Test multiple scenarios
    2. Handle errors gracefully
    3. Return meaningful metrics
    4. Balance multiple objectives
    """
    # Test correctness
    correctness = test_correctness(program_code)
    
    # Test performance
    performance = test_performance(program_code)
    
    # Measure complexity
    complexity = measure_complexity(program_code)
    
    return {
        "objective": correctness * performance,
        "complexity": complexity,
        "performance": performance
    }
```

## Next Steps

You're now ready to explore AlphaEvolve's full capabilities:

1. **Learn More**: Read the complete [User Guide](../user-guide/overview.md)
2. **See Examples**: Explore [real-world examples](../examples/algorithm-optimization.md)
3. **Configure Advanced Features**: Learn about [configuration options](../user-guide/configuration-reference.md)
4. **Understand the API**: Browse the [API Reference](../api-reference/task-utils.md)

## Getting Help

If you encounter issues:

- Check the [User Guide](../user-guide/overview.md) for detailed explanations
- Look at [Examples](../examples/algorithm-optimization.md) for similar use cases
- Ask questions in [GitHub Discussions](https://github.com/alphaevolve/alphaevolve/discussions)
- Report bugs in [GitHub Issues](https://github.com/alphaevolve/alphaevolve/issues)

## Advanced Quick Start

For experienced users who want to jump into advanced features:

```bash
# Set up with production configuration
alphaevolve setup --template production

# Run with checkpointing and resume capability
alphaevolve evolve --source complex_algorithm.py --generations 100 --interactive --checkpoint-interval 10

# Manage evolution checkpoints
alphaevolve checkpoint list
alphaevolve checkpoint resume --checkpoint evolution_checkpoint_gen50_20240101_120000

# Analyze results in different formats
alphaevolve analyze --database results.json --format csv --top 20
```

Ready to evolve your code? Let's start building something amazing!