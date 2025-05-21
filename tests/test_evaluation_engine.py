"""
Tests for the EvaluationEngine class.
"""

import os
import pytest
import asyncio
from typing import Dict, Any

from alpha_evolve.evaluation_engine import EvaluationEngine
from alpha_evolve.task_utils import EvaluationError


# Sample evaluation function that expects a namespace with a specific function
def evaluate_function_in_namespace(namespace: Dict[str, Any]) -> Dict[str, float]:
    """Test evaluation function that looks for 'solution_function_to_evaluate' in the namespace."""
    if "solution_function_to_evaluate" not in namespace:
        raise EvaluationError("Expected 'solution_function_to_evaluate' in namespace")
    
    solution_fn = namespace["solution_function_to_evaluate"]
    
    # Test the function
    try:
        # Test cases
        result1 = solution_fn(5)
        result2 = solution_fn(10)
        
        # Check if the function produces correct results
        if result1 == 25 and result2 == 100:
            return {"accuracy": 1.0, "performance": 0.9}
        else:
            return {"accuracy": 0.0, "performance": 0.5}
    except Exception as e:
        raise EvaluationError(f"Error calling solution function: {str(e)}")


# Test valid code that defines the expected function
VALID_PROGRAM_CODE = """
def solution_function_to_evaluate(x):
    \"\"\"Return the square of a number.\"\"\"
    return x * x
"""

# Test invalid code with syntax error
SYNTAX_ERROR_CODE = """
def solution_function_to_evaluate(x):
    \"\"\"This function has a syntax error.\"\"\"
    return x * x))  # Extra parenthesis
"""

# Test code with runtime error
RUNTIME_ERROR_CODE = """
def solution_function_to_evaluate(x):
    \"\"\"This function will raise a runtime error.\"\"\"
    return x / 0  # Division by zero
"""

# Test code that doesn't define the expected function
MISSING_FUNCTION_CODE = """
def some_other_function(x):
    \"\"\"This is not the function we're looking for.\"\"\"
    return x * x
"""


@pytest.mark.asyncio
async def test_evaluate_valid_program():
    """Test evaluating a valid program with the expected function."""
    engine = EvaluationEngine()
    result = await engine.evaluate_program(VALID_PROGRAM_CODE, evaluate_function_in_namespace)
    
    assert "error" not in result
    assert "accuracy" in result
    assert "performance" in result
    assert result["accuracy"] == 1.0
    assert result["performance"] == 0.9


@pytest.mark.asyncio
async def test_evaluate_syntax_error():
    """Test evaluating a program with syntax errors."""
    engine = EvaluationEngine()
    result = await engine.evaluate_program(SYNTAX_ERROR_CODE, evaluate_function_in_namespace)
    
    assert "error" in result
    assert result["error"] is True
    assert "error_type" in result
    assert result["error_type"] == "SyntaxError"


@pytest.mark.asyncio
async def test_evaluate_runtime_error():
    """Test evaluating a program that raises a runtime error during evaluation."""
    engine = EvaluationEngine()
    result = await engine.evaluate_program(RUNTIME_ERROR_CODE, evaluate_function_in_namespace)
    
    assert "error" in result
    assert result["error"] is True
    assert "error_type" in result


@pytest.mark.asyncio
async def test_evaluate_missing_function():
    """Test evaluating a program that doesn't define the expected function."""
    engine = EvaluationEngine()
    result = await engine.evaluate_program(MISSING_FUNCTION_CODE, evaluate_function_in_namespace)
    
    assert "error" in result
    assert result["error"] is True
    assert "error_type" in result
    assert result["error_type"] == "EvaluationError"


@pytest.mark.asyncio
async def test_evaluation_with_task_inputs():
    """Test evaluating a program with additional task inputs."""
    # Define a function that uses task inputs
    def evaluate_with_inputs(namespace, threshold=0.5):
        solution_fn = namespace["solution_function_to_evaluate"]
        score = solution_fn(5) / 25  # 1.0 if correct
        return {"score": score if score >= threshold else 0.0}
    
    engine = EvaluationEngine()
    
    # With default threshold
    result1 = await engine.evaluate_program(VALID_PROGRAM_CODE, evaluate_with_inputs)
    assert result1["score"] == 1.0
    
    # With custom threshold from task_inputs
    result2 = await engine.evaluate_program(
        VALID_PROGRAM_CODE, 
        evaluate_with_inputs,
        {"threshold": 0.9}
    )
    assert result2["score"] == 1.0
    
    # With threshold that causes a fail
    result3 = await engine.evaluate_program(
        VALID_PROGRAM_CODE, 
        evaluate_with_inputs,
        {"threshold": 1.1}  # Impossible to meet
    )
    assert result3["score"] == 0.0