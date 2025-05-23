# Writing Evaluation Functions

Evaluation functions are crucial for guiding the evolution process. They determine which code variations are kept and which behavioral dimensions are explored.

## Basic Structure

An evaluation function receives the output of your evolved program and returns metrics:

```python
def evaluate_program(program_output, test_inputs):
    """
    Evaluate the evolved program.
    
    Args:
        program_output: Result from running the evolved code
        test_inputs: The inputs that were passed to the program
    
    Returns:
        dict: Contains 'fitness' and behavioral dimensions
    """
    return {
        'fitness': calculate_fitness(program_output, test_inputs),
        'behavior_dim_1': measure_efficiency(program_output),
        'behavior_dim_2': measure_complexity(program_output)
    }
```

## Required Return Format

Your evaluation function must return a dictionary with:

- **`fitness`**: Primary optimization target (higher is better)
- **Behavioral dimensions**: Additional metrics for diversity (any names)

```python
def evaluate_sorting_algorithm(program_output, test_inputs):
    sorted_array = program_output
    original_array = test_inputs[0]
    
    # Check correctness
    expected = sorted(original_array)
    is_correct = sorted_array == expected
    
    return {
        'fitness': 1.0 if is_correct else 0.0,
        'speed': measure_execution_time(program_output),
        'memory_usage': measure_memory_consumption(program_output),
        'comparisons': count_comparisons(program_output)
    }
```

## Fitness Calculation

### Correctness-Based Fitness

For algorithms where correctness is primary:

```python
def evaluate_mathematical_function(program_output, test_inputs):
    x, expected = test_inputs
    actual = program_output
    
    # Perfect match gets fitness 1.0
    if abs(actual - expected) < 1e-10:
        fitness = 1.0
    else:
        # Fitness decreases with error
        error = abs(actual - expected)
        fitness = 1.0 / (1.0 + error)
    
    return {
        'fitness': fitness,
        'precision': -math.log10(abs(actual - expected) + 1e-10),
        'complexity': count_operations(program_output)
    }
```

### Performance-Based Fitness

When optimizing for performance:

```python
def evaluate_optimization_algorithm(program_output, test_inputs):
    solution, execution_time = program_output
    problem_instance = test_inputs[0]
    
    # Better solutions get higher fitness
    solution_quality = calculate_solution_quality(solution, problem_instance)
    
    # Faster execution gets bonus
    time_bonus = 1.0 / (1.0 + execution_time)
    
    return {
        'fitness': solution_quality * time_bonus,
        'execution_time': execution_time,
        'solution_quality': solution_quality,
        'convergence_rate': measure_convergence(solution)
    }
```

## Behavioral Dimensions

Behavioral dimensions encourage diversity in the evolved population. Choose dimensions that capture different aspects of solution quality:

### For Algorithms

```python
def evaluate_search_algorithm(program_output, test_inputs):
    result, stats = program_output
    
    return {
        'fitness': accuracy_score(result),
        'efficiency': 1.0 / stats['operations_count'],
        'memory_footprint': 1.0 / stats['memory_used'],
        'exploration_breadth': stats['nodes_explored'],
        'solution_path_length': len(stats['path'])
    }
```

### For Mathematical Functions

```python
def evaluate_numerical_method(program_output, test_inputs):
    approximation, iterations = program_output
    true_value = test_inputs[1]
    
    accuracy = 1.0 / (1.0 + abs(approximation - true_value))
    
    return {
        'fitness': accuracy,
        'convergence_speed': 1.0 / iterations,
        'stability': measure_numerical_stability(approximation),
        'monotonicity': check_monotonic_convergence(approximation)
    }
```

### For Data Processing

```python
def evaluate_data_processor(program_output, test_inputs):
    processed_data = program_output
    original_data = test_inputs[0]
    
    return {
        'fitness': calculate_data_quality(processed_data),
        'compression_ratio': len(original_data) / len(processed_data),
        'information_preservation': mutual_information(original_data, processed_data),
        'noise_reduction': signal_to_noise_ratio(processed_data)
    }
```

## Multiple Test Cases

Run your evolved code on multiple test cases for robust evaluation:

```python
def evaluate_with_multiple_cases(program_output_list, test_cases):
    """Evaluate across multiple test cases."""
    fitness_scores = []
    behavior_metrics = []
    
    for program_output, test_case in zip(program_output_list, test_cases):
        # Evaluate single case
        result = evaluate_single_case(program_output, test_case)
        fitness_scores.append(result['fitness'])
        behavior_metrics.append(result)
    
    # Aggregate results
    return {
        'fitness': sum(fitness_scores) / len(fitness_scores),
        'consistency': 1.0 - np.std(fitness_scores),
        'robustness': min(fitness_scores),
        'average_efficiency': np.mean([m['efficiency'] for m in behavior_metrics])
    }
```

## Error Handling

Handle cases where evolved code fails or produces invalid output:

```python
def safe_evaluate(program_output, test_inputs):
    """Evaluation function with error handling."""
    try:
        # Check if output is valid
        if program_output is None:
            return {'fitness': 0.0, 'validity': 0.0}
        
        if not isinstance(program_output, expected_type):
            return {'fitness': 0.0, 'type_correctness': 0.0}
        
        # Normal evaluation
        fitness = calculate_fitness(program_output, test_inputs)
        
        return {
            'fitness': max(0.0, min(1.0, fitness)),  # Clamp to [0,1]
            'validity': 1.0,
            'efficiency': measure_efficiency(program_output)
        }
        
    except Exception as e:
        # Log the error for debugging
        print(f"Evaluation error: {e}")
        return {
            'fitness': 0.0,
            'validity': 0.0,
            'error_type': str(type(e).__name__)
        }
```

## Advanced Evaluation Techniques

### Progressive Difficulty

Gradually increase test difficulty:

```python
def progressive_evaluation(program_output, test_inputs, generation):
    """Increase difficulty over generations."""
    base_fitness = calculate_basic_fitness(program_output, test_inputs)
    
    # Add harder tests as evolution progresses
    if generation > 50:
        hard_test_fitness = evaluate_hard_cases(program_output)
        fitness = 0.7 * base_fitness + 0.3 * hard_test_fitness
    else:
        fitness = base_fitness
    
    return {
        'fitness': fitness,
        'generation': generation,
        'test_difficulty': min(generation / 100.0, 1.0)
    }
```

### Multi-Objective Optimization

Balance multiple competing objectives:

```python
def multi_objective_evaluation(program_output, test_inputs):
    """Balance accuracy, speed, and simplicity."""
    accuracy = calculate_accuracy(program_output, test_inputs)
    speed = measure_speed(program_output)
    simplicity = measure_code_simplicity(program_output)
    
    # Weighted combination
    fitness = 0.5 * accuracy + 0.3 * speed + 0.2 * simplicity
    
    return {
        'fitness': fitness,
        'accuracy': accuracy,
        'speed': speed,
        'simplicity': simplicity,
        'pareto_rank': calculate_pareto_rank([accuracy, speed, simplicity])
    }
```

## Best Practices

### Design Principles

1. **Clear objectives**: Define what "better" means for your specific problem
2. **Multiple dimensions**: Include 3-5 behavioral dimensions for diversity
3. **Robust testing**: Use diverse test cases that cover edge cases
4. **Error tolerance**: Handle invalid outputs gracefully
5. **Consistent scaling**: Normalize metrics to similar ranges

### Common Pitfalls

```python
# Avoid: Fitness always returns the same value
def bad_evaluation(program_output, test_inputs):
    return {'fitness': 1.0}  # No selection pressure!

# Avoid: Only checking one simple case
def insufficient_evaluation(program_output, test_inputs):
    if program_output == 42:
        return {'fitness': 1.0}
    return {'fitness': 0.0}

# Good: Comprehensive evaluation
def good_evaluation(program_output, test_inputs):
    fitness = 0.0
    for test_case in test_inputs:
        result = run_test_case(program_output, test_case)
        fitness += evaluate_result(result)
    
    return {
        'fitness': fitness / len(test_inputs),
        'consistency': measure_consistency(program_output, test_inputs),
        'robustness': measure_robustness(program_output, test_inputs)
    }
```

### Testing Your Evaluation Function

Before running evolution, test your evaluation function:

```python
def test_evaluation_function():
    """Test the evaluation function with known good/bad examples."""
    
    # Test with perfect solution
    perfect_output = generate_perfect_solution()
    perfect_score = evaluate_program(perfect_output, test_cases)
    assert perfect_score['fitness'] == 1.0
    
    # Test with terrible solution
    bad_output = generate_bad_solution()
    bad_score = evaluate_program(bad_output, test_cases)
    assert bad_score['fitness'] < 0.5
    
    # Test with invalid output
    invalid_score = evaluate_program(None, test_cases)
    assert invalid_score['fitness'] == 0.0
    
    print("Evaluation function tests passed!")
```

## Next Steps

- [Configure and run evolution](running-evolution.md)
- [Monitor evolution progress](monitoring.md)
- [See evaluation examples](../examples/basic-optimization.md)