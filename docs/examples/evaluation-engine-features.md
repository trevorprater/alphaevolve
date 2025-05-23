# Evaluation Engine Advanced Features

This guide demonstrates how to use the advanced evaluation features introduced in the production-grade evaluation engine.

> **Note:** This documentation is automatically updated when evaluation engine features are modified. Last updated: January 2025 (Task 17, 18-5)

## Evaluation Cascades

Evaluation cascades allow you to apply increasingly complex evaluations with early exit conditions:

```python
from alpha_evolve.evaluation_engine import EvaluationEngine

# Define evaluation functions with increasing complexity
def quick_syntax_check(code, inputs):
    """Fast syntax validation - returns 0.0 for invalid syntax, 1.0 for valid"""
    try:
        compile(code, '<string>', 'exec')
        return 1.0
    except SyntaxError:
        return 0.0

def performance_test(code, inputs):
    """Medium complexity - test performance on small inputs"""
    import time
    start = time.time()
    try:
        exec(code, inputs)
        duration = time.time() - start
        return max(0.0, 1.0 - duration)  # Faster is better
    except Exception:
        return 0.0

def comprehensive_test(code, inputs):
    """Expensive - full test suite"""
    # Run comprehensive test suite
    test_results = []
    for test_case in inputs.get('test_cases', []):
        try:
            result = eval(code, test_case)
            test_results.append(result == test_case['expected'])
        except Exception:
            test_results.append(False)
    return sum(test_results) / len(test_results) if test_results else 0.0

# Configure evaluation cascade
cascade_config = [
    {
        'name': 'syntax_check',
        'threshold': 0.9,  # Must pass syntax check
        'evaluation_fn': quick_syntax_check
    },
    {
        'name': 'performance_test',
        'threshold': 0.7,  # Must meet performance threshold
        'evaluation_fn': performance_test
    },
    {
        'name': 'comprehensive_test',
        'threshold': 0.0,  # Always run if previous stages pass
        'evaluation_fn': comprehensive_test
    }
]

# Apply cascade evaluation
engine = EvaluationEngine()
result = await engine._apply_evaluation_cascades(
    program_code_string="def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
    cascades=cascade_config
)

print(f"Stages completed: {result['stages_completed']}")
print(f"Final score: {result['final_score']}")
print(f"Early exit at: {result.get('early_exit_stage', 'No early exit')}")
```

## Fitness Approximation

Use fitness approximation to speed up expensive evaluations:

```python
from alpha_evolve.evaluation_engine import FitnessApproximator

# Initialize approximator with caching
approximator = FitnessApproximator(
    cache_size=1000,
    approximation_threshold=0.8,  # Use approximation when confidence > 80%
    k_neighbors=5
)

# First, build up cache with some exact evaluations
exact_codes = [
    "def sort_list(lst): return sorted(lst)",
    "def sort_list(lst): return lst.sort() or lst",
    "def sort_list(lst): return bubble_sort(lst)"
]

for code in exact_codes:
    score = expensive_evaluation_function(code)
    approximator.cache_result(code, score, {'algorithm': 'sorting'})

# Now use approximation for similar code
new_code = "def sort_list(lst): return quick_sort(lst)"
approx_score, confidence = approximator.approximate_fitness(
    new_code, 
    {'algorithm': 'sorting'}
)

if confidence > 0.8:
    print(f"Using approximated score: {approx_score} (confidence: {confidence})")
else:
    # Fall back to exact evaluation
    exact_score = expensive_evaluation_function(new_code)
    approximator.cache_result(new_code, exact_score, {'algorithm': 'sorting'})
    print(f"Using exact score: {exact_score}")

# Monitor cache performance
stats = approximator.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")
print(f"Cache size: {stats['size']}/{stats['max_size']}")
```

## Parallel Evaluation

Evaluate multiple programs concurrently for better performance:

```python
import asyncio
from alpha_evolve.evaluation_engine import EvaluationEngine

async def evaluate_population():
    engine = EvaluationEngine()
    
    # List of program variations to evaluate
    programs = [
        "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
        "def fibonacci(n): \n    if n <= 1: return n\n    a, b = 0, 1\n    for _ in range(2, n+1): a, b = b, a + b\n    return b",
        "def fibonacci(n): return int((((1+5**0.5)/2)**n - ((1-5**0.5)/2)**n) / 5**0.5)",
    ]
    
    # Parallel evaluation with concurrency limit
    results = await engine.evaluate_programs_parallel(
        programs,
        task_inputs={'test_cases': [{'n': 10, 'expected': 55}]},
        max_concurrent=3
    )
    
    for i, result in enumerate(results):
        print(f"Program {i+1}: Score = {result['score']:.3f}, "
              f"Time = {result['evaluation_time']:.3f}s")
    
    return results

# Run parallel evaluation
results = asyncio.run(evaluate_population())
```

## Comprehensive Example: Evolution with Advanced Evaluation

Here's a complete example combining all features:

```python
import asyncio
from alpha_evolve.evaluation_engine import EvaluationEngine, FitnessApproximator

class AdvancedEvolutionController:
    def __init__(self):
        self.engine = EvaluationEngine()
        self.approximator = FitnessApproximator(cache_size=5000)
        
        # Define evaluation cascade
        self.cascade = [
            {
                'name': 'syntax_check',
                'threshold': 1.0,
                'evaluation_fn': self._syntax_check
            },
            {
                'name': 'unit_tests',
                'threshold': 0.8,
                'evaluation_fn': self._run_unit_tests
            },
            {
                'name': 'performance_tests',
                'threshold': 0.6,
                'evaluation_fn': self._performance_tests
            },
            {
                'name': 'integration_tests',
                'threshold': 0.0,
                'evaluation_fn': self._integration_tests
            }
        ]
    
    def _syntax_check(self, code, inputs):
        try:
            compile(code, '<string>', 'exec')
            return 1.0
        except SyntaxError:
            return 0.0
    
    def _run_unit_tests(self, code, inputs):
        # Simulate unit test execution
        import random
        return random.uniform(0.5, 1.0)
    
    def _performance_tests(self, code, inputs):
        # Simulate performance testing
        import random
        return random.uniform(0.3, 0.9)
    
    def _integration_tests(self, code, inputs):
        # Simulate integration testing
        import random
        return random.uniform(0.0, 0.8)
    
    async def evaluate_generation(self, programs, task_inputs):
        """Evaluate a generation of programs using all advanced features"""
        
        # First, try approximation for known similar programs
        quick_results = []
        expensive_programs = []
        
        for program in programs:
            approx_score, confidence = self.approximator.approximate_fitness(
                program, task_inputs
            )
            
            if confidence > 0.85:
                quick_results.append({
                    'score': approx_score,
                    'approximated': True,
                    'confidence': confidence
                })
            else:
                expensive_programs.append(program)
                quick_results.append(None)  # Placeholder
        
        # Parallel evaluation for programs requiring exact computation
        if expensive_programs:
            exact_results = await self.engine.evaluate_programs_parallel(
                expensive_programs,
                task_inputs,
                max_concurrent=4
            )
            
            # Cache exact results and apply cascades if needed
            exact_idx = 0
            for i, result in enumerate(quick_results):
                if result is None:  # Needs exact evaluation
                    program = programs[i]
                    
                    # Apply evaluation cascade
                    cascade_result = await self.engine._apply_evaluation_cascades(
                        program, self.cascade
                    )
                    
                    final_score = cascade_result['final_score']
                    
                    # Cache the result
                    self.approximator.cache_result(program, final_score, task_inputs)
                    
                    quick_results[i] = {
                        'score': final_score,
                        'approximated': False,
                        'cascade_stages': cascade_result['stages_completed'],
                        'early_exit': cascade_result.get('early_exit_stage')
                    }
                    exact_idx += 1
        
        return quick_results
    
    def get_evaluation_stats(self):
        """Get performance statistics"""
        cache_stats = self.approximator.get_cache_stats()
        return {
            'cache_hit_rate': cache_stats['hit_rate'],
            'cache_utilization': cache_stats['size'] / cache_stats['max_size'],
            'approximation_savings': cache_stats.get('approximation_count', 0)
        }

# Usage example
async def main():
    controller = AdvancedEvolutionController()
    
    # Sample programs to evaluate
    programs = [
        "def quicksort(arr): return arr if len(arr) <= 1 else quicksort([x for x in arr[1:] if x <= arr[0]]) + [arr[0]] + quicksort([x for x in arr[1:] if x > arr[0]])",
        "def quicksort(arr): arr.sort(); return arr",
        "def quicksort(arr): import heapq; return list(heapq.nsmallest(len(arr), arr))"
    ]
    
    task_inputs = {'test_arrays': [[3,1,4,1,5], [9,2,6,5,3,5]]}
    
    # Evaluate generation
    results = await controller.evaluate_generation(programs, task_inputs)
    
    # Print results
    for i, result in enumerate(results):
        approx_str = "approximated" if result['approximated'] else "exact"
        print(f"Program {i+1}: {result['score']:.3f} ({approx_str})")
    
    # Print performance stats
    stats = controller.get_evaluation_stats()
    print(f"\nEvaluation Statistics:")
    print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
    print(f"Cache utilization: {stats['cache_utilization']:.2%}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Diversity-Aware Evaluation Integration

The evaluation engine works seamlessly with the advanced diversity metrics system for comprehensive program assessment:

```python
from alpha_evolve.diversity_metrics import get_diversity_metric
from alpha_evolve.advanced_map_elites import CVTMAPElitesArchive
from alpha_evolve.evaluation_engine import EvaluationEngine

class DiversityAwareEvaluationController:
    def __init__(self):
        self.engine = EvaluationEngine()
        self.diversity_metric = get_diversity_metric()
        self.archive = CVTMAPElitesArchive(feature_dimensions=3, num_centroids=100)
    
    async def evaluate_with_diversity(self, programs, task_inputs):
        """Evaluate programs considering both performance and diversity"""
        
        # Standard performance evaluation
        performance_results = await self.engine.evaluate_programs_parallel(
            programs, task_inputs, max_concurrent=4
        )
        
        # Calculate diversity scores for archive integration
        enhanced_results = []
        
        for i, (program, perf_result) in enumerate(zip(programs, performance_results)):
            # Get diverse elites from archive for comparison
            diverse_elites = self.archive.get_diverse_elites(count=10, diversity_threshold=0.3)
            
            # Calculate diversity to existing archive members
            diversity_scores = []
            for elite in diverse_elites:
                div_score = self.diversity_metric.calculate_diversity(program, elite.code)
                diversity_scores.append(div_score.total_score)
            
            avg_diversity = sum(diversity_scores) / len(diversity_scores) if diversity_scores else 0.5
            
            enhanced_result = {
                'performance_score': perf_result['score'],
                'diversity_score': avg_diversity,
                'combined_score': perf_result['score'] * 0.7 + avg_diversity * 0.3,
                'semantic_diversity': sum(ds.semantic_score for ds in 
                                        [self.diversity_metric.calculate_diversity(program, e.code) 
                                         for e in diverse_elites[:5]]) / 5 if diverse_elites else 0.0,
                'structural_diversity': sum(ds.structural_score for ds in 
                                          [self.diversity_metric.calculate_diversity(program, e.code) 
                                           for e in diverse_elites[:5]]) / 5 if diverse_elites else 0.0
            }
            enhanced_results.append(enhanced_result)
        
        return enhanced_results
    
    def get_archive_diversity_stats(self):
        """Get comprehensive diversity statistics from the archive"""
        return self.archive.get_diversity_statistics()

# Usage example with diversity-aware evaluation
async def diversity_evaluation_example():
    controller = DiversityAwareEvaluationController()
    
    # Sample programs with varying approaches
    programs = [
        # Recursive approach
        "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
        # Iterative approach  
        "def factorial(n):\n    result = 1\n    for i in range(1, n+1): result *= i\n    return result",
        # Mathematical approach
        "def factorial(n): import math; return math.factorial(n)",
        # Functional approach
        "def factorial(n): from functools import reduce; return reduce(lambda x, y: x*y, range(1, n+1), 1)"
    ]
    
    task_inputs = {'test_cases': [{'n': 5, 'expected': 120}]}
    
    # Evaluate with diversity awareness
    results = await controller.evaluate_with_diversity(programs, task_inputs)
    
    print("Diversity-Aware Evaluation Results:")
    for i, result in enumerate(results):
        print(f"Program {i+1}:")
        print(f"  Performance: {result['performance_score']:.3f}")
        print(f"  Diversity: {result['diversity_score']:.3f}")
        print(f"  Combined: {result['combined_score']:.3f}")
        print(f"  Semantic Diversity: {result['semantic_diversity']:.3f}")
        print(f"  Structural Diversity: {result['structural_diversity']:.3f}")
        print()
    
    # Show archive diversity statistics
    diversity_stats = controller.get_archive_diversity_stats()
    print("Archive Diversity Statistics:")
    print(f"  Average Diversity: {diversity_stats['avg_diversity_per_cell']:.3f}")
    print(f"  Archive Diversity Score: {diversity_stats['archive_diversity_score']:.3f}")
    print(f"  Diversity Mode Enabled: {diversity_stats['diversity_mode_enabled']}")

# Run the diversity-aware example
asyncio.run(diversity_evaluation_example())
```

## Best Practices

1. **Cascade Design**: Order evaluations from fastest to most expensive, with appropriate thresholds
2. **Approximation Tuning**: Start with high confidence thresholds (0.8+) and adjust based on accuracy needs
3. **Parallel Evaluation**: Use concurrency limits to avoid overwhelming system resources
4. **Cache Management**: Monitor hit rates and adjust cache size based on memory constraints
5. **Feature Engineering**: Design meaningful features for approximation (code complexity, algorithm type, etc.)
6. **Diversity Integration**: Balance performance and diversity scores based on exploration vs. exploitation needs
7. **Archive Maintenance**: Use diversity-aware elite selection to maintain high-quality, diverse program populations

## Performance Tuning

- **Cache Size**: Larger caches improve hit rates but use more memory
- **K-Neighbors**: More neighbors improve approximation accuracy but increase computation
- **Concurrency**: Balance parallelism with system resources and evaluation complexity
- **Threshold Tuning**: Adjust cascade thresholds based on evaluation cost vs. accuracy trade-offs
- **Diversity Sampling**: Use sampling strategies for large archives to maintain O(k²) complexity instead of O(n²)
- **Archive Integration**: Configure diversity thresholds based on archive size and exploration requirements