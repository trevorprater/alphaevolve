# User Guide Overview

This user guide provides comprehensive information about using AlphaEvolve to evolve and optimize your code using evolutionary algorithms and Large Language Models.

## How AlphaEvolve Works

AlphaEvolve follows a systematic approach to code evolution:

1. **Code Analysis**: Identifies evolvable code blocks in your program
2. **Population Management**: Maintains a population of code variations using MAP-Elites
3. **LLM-Driven Mutations**: Uses LLMs to generate intelligent code modifications
4. **Evaluation**: Tests each variation using your custom evaluation functions
5. **Selection**: Keeps the best variations based on multiple behavioral dimensions
6. **Iteration**: Repeats the process to continuously improve your code

## Key Concepts

### Evolvable Code Blocks

Code sections marked with special comments that AlphaEvolve can modify:

```python
# EVOLVABLE_START: function_name
def my_function(x):
    return x * 2
# EVOLVABLE_END
```

### Behavioral Dimensions

AlphaEvolve uses MAP-Elites to maintain diversity across multiple behavioral dimensions. These dimensions are defined by your evaluation function and help ensure the system explores different solution strategies.

### Evaluation Functions

Custom functions that measure the quality and behavior of evolved code:

```python
def evaluate_program(program_output, inputs):
    """Evaluate the evolved program."""
    accuracy = calculate_accuracy(program_output, inputs)
    efficiency = measure_efficiency(program_output)
    return {
        'fitness': accuracy,
        'behavior_dim_1': efficiency,
        'behavior_dim_2': complexity_score(program_output)
    }
```

## Workflow Overview

### 1. Prepare Your Code

- Mark evolvable sections with `EVOLVABLE_START` and `EVOLVABLE_END` comments
- Ensure your code has a clear entry point
- Write comprehensive evaluation functions

### 2. Configure Evolution

- Set up your `evolution_config.yaml`
- Configure LLM providers and models
- Define evolution parameters (population size, generations, etc.)

### 3. Run Evolution

```bash
# Start evolution with monitoring
alphaevolve evolve --config evolution_config.yaml --monitor

# Resume from checkpoint
alphaevolve evolve --resume checkpoints/latest.json
```

### 4. Monitor Progress

- View real-time progress in the terminal
- Check detailed logs and metrics
- Analyze population diversity and fitness trends

### 5. Analyze Results

```bash
# View best programs
alphaevolve analyze --archive results/archive.json --top 10

# Export results
alphaevolve analyze --export results/best_programs.json
```

## Best Practices

### Code Preparation

- Keep evolvable blocks focused and well-defined
- Provide comprehensive test cases in your evaluation function
- Use meaningful variable names and clear logic structure
- Avoid external dependencies within evolvable blocks when possible

### Evaluation Design

- Define multiple behavioral dimensions to encourage diversity
- Balance fitness and behavioral measurements
- Include edge cases and stress tests
- Ensure evaluation functions are deterministic

### Evolution Configuration

- Start with smaller populations for quick experimentation
- Use appropriate LLM models for your code complexity
- Set reasonable timeout values for LLM calls
- Configure proper checkpoint intervals

### Monitoring and Analysis

- Save checkpoints regularly during long runs
- Monitor population diversity to avoid premature convergence
- Analyze behavioral dimension distributions
- Keep detailed logs for post-evolution analysis

## Common Use Cases

### Algorithm Optimization

Evolve sorting algorithms, search algorithms, or mathematical functions to improve performance or find novel approaches.

### Code Refactoring

Automatically refactor code sections to improve readability, efficiency, or maintainability while preserving functionality.

### Creative Programming

Generate creative solutions to programming challenges by exploring unconventional approaches through evolutionary search.

### Performance Tuning

Optimize performance-critical code sections by evolving different implementation strategies and measuring their effectiveness.

## Next Steps

- [Mark your code with evolvable blocks](marking-code.md)
- [Write effective evaluation functions](evaluation-functions.md)
- [Configure and run evolution](running-evolution.md)
- [Monitor evolution progress](monitoring.md)