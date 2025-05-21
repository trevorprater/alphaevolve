"""
Unit tests for the task_utils module.
"""

import os
import pytest
import sys
from pathlib import Path

from alpha_evolve.task_utils import (
    TaskDefinition,
    CodeParser,
    CodeParsingError,
    EvaluationWrapper,
    EvaluationError
)


class TestTaskDefinition:
    """Tests for the TaskDefinition dataclass."""

    def test_initialization(self):
        """Test initialization of TaskDefinition with valid data."""
        task = TaskDefinition(
            problem_name="test_problem",
            initial_code_path="/path/to/code.py",
            evaluate_function_module_path="/path/to/eval.py",
            evaluate_function_name="evaluate_fn"
        )

        assert task.problem_name == "test_problem"
        assert task.initial_code_path == "/path/to/code.py"
        assert task.evaluate_function_module_path == "/path/to/eval.py"
        assert task.evaluate_function_name == "evaluate_fn"


class TestCodeParser:
    """Tests for the CodeParser class."""

    def test_extract_single_evolvable_block(self):
        """Test extraction of a single evolvable block."""
        code = """
def hello():
    print("Hello World")

# EVOLVE-BLOCK-START block1
def function_to_evolve():
    return 42
# EVOLVE-BLOCK-END block1

def goodbye():
    print("Goodbye")
"""
        blocks = CodeParser.extract_evolvable_blocks(code)
        
        assert len(blocks) == 1
        block_id, block_code = blocks[0]
        
        assert block_id == "block1"
        assert "def function_to_evolve():" in block_code
        assert "return 42" in block_code

    def test_extract_multiple_evolvable_blocks(self):
        """Test extraction of multiple evolvable blocks."""
        code = """
# EVOLVE-BLOCK-START block1
def function1():
    return 1
# EVOLVE-BLOCK-END block1

# Regular code
x = 10

# EVOLVE-BLOCK-START block2
def function2():
    return 2
# EVOLVE-BLOCK-END block2
"""
        blocks = CodeParser.extract_evolvable_blocks(code)
        
        assert len(blocks) == 2
        
        # Check first block
        assert blocks[0][0] == "block1"
        assert "def function1():" in blocks[0][1]
        assert "return 1" in blocks[0][1]
        
        # Check second block
        assert blocks[1][0] == "block2"
        assert "def function2():" in blocks[1][1]
        assert "return 2" in blocks[1][1]

    def test_extract_no_evolvable_blocks(self):
        """Test extraction with no evolvable blocks in the code."""
        code = """
def function():
    return 42

# This is just a regular comment
x = 10
"""
        blocks = CodeParser.extract_evolvable_blocks(code)
        assert len(blocks) == 0

    def test_nested_comment_markers(self):
        """Test handling of nested comment markers (should extract based on matching IDs)."""
        code = """
# EVOLVE-BLOCK-START outer
def outer_function():
    # EVOLVE-BLOCK-START inner
    def inner_function():
        return "inner"
    # EVOLVE-BLOCK-END inner
    return "outer"
# EVOLVE-BLOCK-END outer
"""
        blocks = CodeParser.extract_evolvable_blocks(code)
        
        assert len(blocks) == 2
        
        # Blocks should be identified by their IDs
        block_ids = [block[0] for block in blocks]
        assert "outer" in block_ids
        assert "inner" in block_ids
        
        # Check content of inner block
        inner_block = next(block for block in blocks if block[0] == "inner")
        assert "def inner_function():" in inner_block[1]
        
        # Check content of outer block
        outer_block = next(block for block in blocks if block[0] == "outer")
        assert "def outer_function():" in outer_block[1]

    def test_empty_evolvable_block(self):
        """Test extraction of an evolvable block with no content."""
        code = """
# EVOLVE-BLOCK-START empty
# EVOLVE-BLOCK-END empty
"""
        blocks = CodeParser.extract_evolvable_blocks(code)
        
        assert len(blocks) == 1
        assert blocks[0][0] == "empty"
        assert blocks[0][1].strip() == ""

    def test_mismatched_start_marker(self):
        """Test that an exception is raised when a start marker has no matching end marker."""
        code = """
# EVOLVE-BLOCK-START unmatched
def function():
    return 42
# No matching end marker
"""
        with pytest.raises(CodeParsingError) as excinfo:
            CodeParser.extract_evolvable_blocks(code)
        
        assert "no matching end marker" in str(excinfo.value).lower()

    def test_mismatched_end_marker(self):
        """Test that an exception is raised when an end marker has no matching start marker."""
        code = """
# No matching start marker
def function():
    return 42
# EVOLVE-BLOCK-END unmatched
"""
        with pytest.raises(CodeParsingError) as excinfo:
            CodeParser.extract_evolvable_blocks(code)
        
        assert "no matching start marker" in str(excinfo.value).lower()


class TestEvaluationWrapper:
    """Tests for the EvaluationWrapper class."""
    
    @pytest.fixture
    def evaluation_wrapper(self):
        """Fixture to create an EvaluationWrapper instance."""
        return EvaluationWrapper()
    
    @pytest.fixture
    def dummy_eval_module(self, tmp_path):
        """
        Fixture to create a temporary Python module with evaluation functions.
        
        Returns the path to the module and creates these functions:
        - valid_eval_fn: Returns a valid score dict
        - invalid_eval_fn: Returns a non-dict value
        - error_eval_fn: Raises an exception
        """
        module_dir = tmp_path / "eval_modules"
        module_dir.mkdir()
        
        module_path = module_dir / "dummy_eval.py"
        
        with open(module_path, "w") as f:
            f.write("""
def valid_eval_fn(program, **kwargs):
    # A valid evaluation function that returns a dict of scores
    return {"accuracy": 0.95, "speed": 0.8}

def invalid_eval_fn(program, **kwargs):
    # An invalid evaluation function that returns a non-dict
    return "not a dict"

def error_eval_fn(program, **kwargs):
    # An evaluation function that raises an exception
    raise ValueError("Simulated error in evaluation function")
""")
        
        return str(module_path)

    def test_load_valid_evaluate_function(self, evaluation_wrapper, dummy_eval_module):
        """Test loading a valid evaluation function."""
        fn = evaluation_wrapper.load_user_evaluate_function(
            dummy_eval_module, "valid_eval_fn"
        )
        
        assert callable(fn)
        result = fn(None)  # Call with None as the program
        assert isinstance(result, dict)
        assert result["accuracy"] == 0.95
        assert result["speed"] == 0.8

    def test_load_from_nonexistent_module(self, evaluation_wrapper, tmp_path):
        """Test attempting to load from a non-existent module."""
        nonexistent_path = tmp_path / "does_not_exist.py"
        
        with pytest.raises(EvaluationError) as excinfo:
            evaluation_wrapper.load_user_evaluate_function(
                str(nonexistent_path), "some_function"
            )
        
        # Since the actual error message is "Error loading evaluation function: [Errno 2] No such file or directory"
        # we just check for a basic part of the error message
        assert "no such file" in str(excinfo.value).lower()

    def test_load_nonexistent_function(self, evaluation_wrapper, dummy_eval_module):
        """Test attempting to load a non-existent function from an existing module."""
        with pytest.raises(EvaluationError) as excinfo:
            evaluation_wrapper.load_user_evaluate_function(
                dummy_eval_module, "nonexistent_function"
            )
        
        assert "not found in module" in str(excinfo.value).lower()

    def test_run_valid_evaluation(self, evaluation_wrapper, dummy_eval_module):
        """Test running a valid evaluation function."""
        # First load the valid evaluation function
        valid_fn = evaluation_wrapper.load_user_evaluate_function(
            dummy_eval_module, "valid_eval_fn"
        )
        
        # Then run the evaluation
        result = evaluation_wrapper.run_evaluation(
            "dummy_program", valid_fn, {"param1": "value1"}
        )
        
        assert isinstance(result, dict)
        assert result["accuracy"] == 0.95
        assert result["speed"] == 0.8

    def test_run_evaluation_with_error(self, evaluation_wrapper, dummy_eval_module):
        """Test running an evaluation function that raises an exception."""
        # First load the error-raising evaluation function
        error_fn = evaluation_wrapper.load_user_evaluate_function(
            dummy_eval_module, "error_eval_fn"
        )
        
        # Then run the evaluation, expecting an EvaluationError
        with pytest.raises(EvaluationError) as excinfo:
            evaluation_wrapper.run_evaluation("dummy_program", error_fn)
        
        assert "error during program evaluation" in str(excinfo.value).lower()

    def test_run_evaluation_with_invalid_return(self, evaluation_wrapper, dummy_eval_module):
        """Test running an evaluation function that returns a non-dict value."""
        # First load the invalid evaluation function
        invalid_fn = evaluation_wrapper.load_user_evaluate_function(
            dummy_eval_module, "invalid_eval_fn"
        )
        
        # Then run the evaluation, expecting an EvaluationError
        with pytest.raises(EvaluationError) as excinfo:
            evaluation_wrapper.run_evaluation("dummy_program", invalid_fn)
        
        assert "must return a dictionary" in str(excinfo.value).lower()