"""
Comprehensive tests for diversity metrics implementation in AlphaEvolve.

Tests cover semantic similarity, behavioral diversity, structural diversity,
textual diversity, and composite diversity metrics.
"""

import pytest
import numpy as np
from typing import Dict, Any

from alpha_evolve.diversity_metrics import (
    SemanticSimilarityMetric,
    BehavioralDiversityMetric,
    StructuralDiversityMetric,
    TextualDiversityMetric,
    CompositeDiversityMetric,
    DiversityScore,
    get_diversity_metric,
    calculate_program_diversity
)


class TestSemanticSimilarityMetric:
    """Test semantic similarity metric functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metric = SemanticSimilarityMetric()
    
    def test_identical_code_zero_diversity(self):
        """Test that identical code has zero diversity."""
        code = "def add(x, y):\n    return x + y"
        
        diversity = self.metric.calculate_diversity(code, code)
        assert diversity == 0.0
    
    def test_different_functions_high_diversity(self):
        """Test that different functions have high diversity."""
        code1 = "def add(x, y):\n    return x + y"
        code2 = "def multiply(a, b):\n    return a * b"
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.0  # Should have some diversity (functions are structurally similar)
    
    def test_similar_structure_low_diversity(self):
        """Test that similar structures have low diversity."""
        code1 = """
def process_list(items):
    result = []
    for item in items:
        result.append(item * 2)
    return result
"""
        
        code2 = """
def transform_data(data):
    output = []
    for element in data:
        output.append(element + 1)
    return output
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert 0.0 < diversity < 0.8  # Some diversity but not maximum (very similar structure)
    
    def test_class_vs_function_diversity(self):
        """Test diversity between class and function definitions."""
        code1 = """
def calculate(x):
    return x * 2
"""
        
        code2 = """
class Calculator:
    def __init__(self):
        self.value = 0
    
    def calculate(self, x):
        return x * 2
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.1  # Should be different structurally (class vs function)
    
    def test_syntax_error_fallback(self):
        """Test fallback behavior with syntax errors."""
        code1 = "def valid_function():\n    return 42"
        code2 = "def invalid_function(\n    return 42"  # Syntax error
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert 0.0 <= diversity <= 1.0  # Should handle gracefully
    
    def test_control_flow_differences(self):
        """Test diversity based on control flow differences."""
        code1 = """
def simple_function(x):
    return x + 1
"""
        
        code2 = """
def complex_function(x):
    if x > 0:
        while x > 10:
            x -= 1
        return x + 1
    else:
        return 0
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.1  # Complex control flow should increase diversity


class TestBehavioralDiversityMetric:
    """Test behavioral diversity metric functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metric = BehavioralDiversityMetric()
    
    def test_identical_behavior_zero_diversity(self):
        """Test that identical behavior has low diversity."""
        code = "def factorial(n):\n    return 1 if n <= 1 else n * factorial(n-1)"
        
        diversity = self.metric.calculate_diversity(code, code)
        assert diversity == 0.0
    
    def test_different_algorithms_high_diversity(self):
        """Test that different algorithms have high diversity."""
        code1 = """
def iterative_factorial(n):
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
"""
        
        code2 = """
def recursive_factorial(n):
    return 1 if n <= 1 else n * recursive_factorial(n-1)
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.2  # Different algorithmic approaches
    
    def test_complexity_differences(self):
        """Test diversity based on complexity differences."""
        code1 = "def simple(x):\n    return x + 1"
        
        code2 = """
def complex(x):
    result = x
    for i in range(10):
        if result % 2 == 0:
            result = result // 2
        else:
            result = result * 3 + 1
    return result
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.2  # Higher complexity should increase diversity
    
    def test_data_structure_usage(self):
        """Test diversity based on data structure usage."""
        code1 = """
def process_with_list(data):
    result = []
    for item in data:
        result.append(item * 2)
    return result
"""
        
        code2 = """
def process_with_dict(data):
    result = {}
    for i, item in enumerate(data):
        result[i] = item * 2
    return result
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.1  # Different data structures should show some diversity
    
    def test_comprehension_usage(self):
        """Test diversity based on comprehension usage."""
        code1 = """
def with_loop(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result
"""
        
        code2 = """
def with_comprehension(items):
    return [item * 2 for item in items if item > 0]
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.2  # Different iteration patterns


class TestStructuralDiversityMetric:
    """Test structural diversity metric functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metric = StructuralDiversityMetric()
    
    def test_identical_structure_zero_diversity(self):
        """Test that identical structure has zero diversity."""
        code = """
class MyClass:
    def __init__(self):
        self.value = 0
    
    def get_value(self):
        return self.value
"""
        
        diversity = self.metric.calculate_diversity(code, code)
        assert diversity == 0.0
    
    def test_function_vs_class_organization(self):
        """Test diversity between function-based and class-based organization."""
        code1 = """
def calculate(x):
    return x * 2

def process(data):
    return [calculate(item) for item in data]
"""
        
        code2 = """
class Calculator:
    @staticmethod
    def calculate(x):
        return x * 2
    
    def process(self, data):
        return [self.calculate(item) for item in data]
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.1  # Different organizational patterns should show some diversity
    
    def test_nested_vs_flat_structure(self):
        """Test diversity between nested and flat structures."""
        code1 = """
def outer_function():
    def inner_function(x):
        return x + 1
    return inner_function(5)
"""
        
        code2 = """
def helper_function(x):
    return x + 1

def main_function():
    return helper_function(5)
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.05  # Different nesting patterns should show some diversity
    
    def test_inheritance_patterns(self):
        """Test diversity based on inheritance patterns."""
        code1 = """
class Base:
    def method(self):
        return "base"

class Derived(Base):
    def method(self):
        return "derived"
"""
        
        code2 = """
class Standalone:
    def method(self):
        return "standalone"
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.1  # Different inheritance patterns should show some diversity
    
    def test_design_pattern_differences(self):
        """Test diversity based on design pattern usage."""
        code1 = """
class Context:
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
"""
        
        code2 = """
def simple_function():
    return "simple"
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.2  # Context manager vs simple function should show diversity


class TestTextualDiversityMetric:
    """Test textual diversity metric functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metric = TextualDiversityMetric()
    
    def test_identical_text_zero_diversity(self):
        """Test that identical text has zero diversity."""
        code = "def hello():\n    print('Hello, World!')"
        
        diversity = self.metric.calculate_diversity(code, code)
        assert diversity == 0.0
    
    def test_different_tokens_high_diversity(self):
        """Test that different tokens increase diversity."""
        code1 = "def calculate_sum(numbers):\n    return sum(numbers)"
        code2 = "def compute_product(values):\n    return reduce(mul, values)"
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.2  # Different vocabulary should show diversity
    
    def test_identifier_naming_styles(self):
        """Test diversity based on naming style differences."""
        code1 = """
def snake_case_function():
    variable_name = 10
    return variable_name
"""
        
        code2 = """
def camelCaseFunction():
    variableName = 10
    return variableName
"""
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.2  # Different naming conventions
    
    def test_comment_and_string_differences(self):
        """Test diversity based on comments and strings."""
        code1 = '''
def function():
    # This is a comment
    return "string literal"
'''
        
        code2 = '''
def function():
    # Different comment here
    return 'alternative string'
'''
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.1  # Some textual differences
    
    def test_lexical_diversity_differences(self):
        """Test diversity based on lexical richness."""
        code1 = "x = x + x + x"  # Low lexical diversity
        
        code2 = """
def calculate_result(input_value, multiplier, offset):
    intermediate = input_value * multiplier
    final_result = intermediate + offset
    return final_result
"""  # High lexical diversity
        
        diversity = self.metric.calculate_diversity(code1, code2)
        assert diversity > 0.3  # Significant lexical differences


class TestCompositeDiversityMetric:
    """Test composite diversity metric functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metric = CompositeDiversityMetric()
    
    def test_identical_code_zero_diversity(self):
        """Test that identical code has zero diversity."""
        code = "def test():\n    return 42"
        
        score = self.metric.calculate_diversity(code, code)
        assert isinstance(score, DiversityScore)
        assert score.total_score == 0.0
        assert score.semantic_score == 0.0
        assert score.behavioral_score == 0.0
        assert score.structural_score == 0.0
        assert score.textual_score == 0.0
    
    def test_completely_different_code_high_diversity(self):
        """Test that completely different code has high diversity."""
        code1 = "def simple():\n    return 1"
        
        code2 = """
class ComplexProcessor:
    def __init__(self, config):
        self.config = config
        self.cache = {}
    
    async def process_data(self, data_stream):
        results = []
        async for item in data_stream:
            if item.id not in self.cache:
                processed = await self._complex_computation(item)
                self.cache[item.id] = processed
            results.append(self.cache[item.id])
        return results
    
    async def _complex_computation(self, item):
        # Complex algorithm implementation
        pass
"""
        
        score = self.metric.calculate_diversity(code1, code2)
        assert score.total_score > 0.4  # Should be quite different
        assert score.semantic_score > 0.3
        assert score.structural_score > 0.2
    
    def test_custom_weights(self):
        """Test composite metric with custom weights."""
        weights = {
            'semantic': 0.5,
            'behavioral': 0.3,
            'structural': 0.1,
            'textual': 0.1
        }
        
        metric = CompositeDiversityMetric(weights)
        assert metric.get_metric_weights() == weights
        
        code1 = "def add(x, y):\n    return x + y"
        code2 = "def subtract(a, b):\n    return a - b"
        
        score = metric.calculate_diversity(code1, code2)
        assert isinstance(score, DiversityScore)
        assert 0.0 <= score.total_score <= 1.0
    
    def test_diversity_score_metadata(self):
        """Test that diversity score includes metadata."""
        code1 = "def func1():\n    pass"
        code2 = "def func2():\n    pass"
        
        score = self.metric.calculate_diversity(code1, code2)
        assert isinstance(score.metadata, dict)
        assert 'semantic_metric' in score.metadata
        assert 'behavioral_metric' in score.metadata
        assert 'structural_metric' in score.metadata
        assert 'textual_metric' in score.metadata
    
    def test_weight_modification(self):
        """Test weight modification functionality."""
        new_weights = {
            'semantic': 0.7,
            'behavioral': 0.2,
            'structural': 0.05,
            'textual': 0.05
        }
        
        self.metric.set_metric_weights(new_weights)
        assert self.metric.get_metric_weights() == new_weights


class TestGlobalDiversityMetricFunctions:
    """Test global diversity metric functions."""
    
    def test_get_diversity_metric_singleton(self):
        """Test that get_diversity_metric returns singleton instance."""
        metric1 = get_diversity_metric()
        metric2 = get_diversity_metric()
        
        assert metric1 is metric2
        assert isinstance(metric1, CompositeDiversityMetric)
    
    def test_calculate_program_diversity_convenience(self):
        """Test convenience function for calculating program diversity."""
        code1 = "def test1():\n    return 1"
        code2 = "def test2():\n    return 2"
        
        score = calculate_program_diversity(code1, code2)
        assert isinstance(score, DiversityScore)
        assert 0.0 <= score.total_score <= 1.0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metric = CompositeDiversityMetric()
    
    def test_empty_code_handling(self):
        """Test handling of empty code strings."""
        score = self.metric.calculate_diversity("", "")
        assert isinstance(score, DiversityScore)
        assert score.total_score < 0.1  # Should be very low (near zero)
    
    def test_one_empty_code_handling(self):
        """Test handling when one code string is empty."""
        code = "def test():\n    return 42"
        empty = ""
        
        score = self.metric.calculate_diversity(code, empty)
        assert isinstance(score, DiversityScore)
        assert score.total_score > 0.3  # Should be quite different
    
    def test_syntax_error_resilience(self):
        """Test resilience to syntax errors."""
        valid_code = "def valid():\n    return 42"
        invalid_code = "def invalid(\n    return 42"  # Missing closing parenthesis
        
        score = self.metric.calculate_diversity(valid_code, invalid_code)
        assert isinstance(score, DiversityScore)
        assert 0.0 <= score.total_score <= 1.0
    
    def test_very_long_code_handling(self):
        """Test handling of very long code strings."""
        long_code1 = "\n".join([f"def func_{i}():\n    return {i}" for i in range(100)])
        long_code2 = "\n".join([f"def method_{i}():\n    return {i * 2}" for i in range(100)])
        
        score = self.metric.calculate_diversity(long_code1, long_code2)
        assert isinstance(score, DiversityScore)
        assert 0.0 <= score.total_score <= 1.0
    
    def test_unicode_and_special_characters(self):
        """Test handling of unicode and special characters."""
        code1 = '''
def process_text():
    text = "Hello, 世界!"
    return text.encode('utf-8')
'''
        
        code2 = '''
def handle_symbols():
    symbols = "→←↑↓∑∏∆∇"
    return len(symbols)
'''
        
        score = self.metric.calculate_diversity(code1, code2)
        assert isinstance(score, DiversityScore)
        assert score.total_score > 0.05  # Should handle unicode characters


class TestPerformanceAndScaling:
    """Test performance characteristics and scaling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.metric = CompositeDiversityMetric()
    
    def test_medium_code_performance(self):
        """Test performance with medium-sized code."""
        import time
        
        code1 = "\n".join([
            "def fibonacci(n):",
            "    if n <= 1:",
            "        return n",
            "    return fibonacci(n-1) + fibonacci(n-2)",
            "",
            "def factorial(n):",
            "    return 1 if n <= 1 else n * factorial(n-1)",
            "",
            "class Calculator:",
            "    def __init__(self):",
            "        self.history = []",
            "    ",
            "    def add(self, a, b):",
            "        result = a + b",
            "        self.history.append(('add', a, b, result))",
            "        return result"
        ])
        
        code2 = "\n".join([
            "def iterative_fibonacci(n):",
            "    a, b = 0, 1",
            "    for _ in range(n):",
            "        a, b = b, a + b",
            "    return a",
            "",
            "def iterative_factorial(n):",
            "    result = 1",
            "    for i in range(1, n + 1):",
            "        result *= i",
            "    return result",
            "",
            "class AdvancedCalculator:",
            "    def __init__(self):",
            "        self.memory = 0",
            "        self.operations = []",
            "    ",
            "    def compute(self, operation, a, b):",
            "        if operation == 'add':",
            "            result = a + b",
            "        else:",
            "            result = 0",
            "        self.operations.append((operation, a, b, result))",
            "        return result"
        ])
        
        start_time = time.time()
        score = self.metric.calculate_diversity(code1, code2)
        end_time = time.time()
        
        # Should complete in reasonable time (< 1 second for medium code)
        assert end_time - start_time < 1.0
        assert isinstance(score, DiversityScore)
        assert 0.0 <= score.total_score <= 1.0


if __name__ == "__main__":
    pytest.main([__file__])