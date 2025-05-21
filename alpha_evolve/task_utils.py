"""
Task definition and parsing utilities for AlphaEvolve.

This module provides the core components for task specification, code parsing,
and evaluation in the AlphaEvolve system.
"""

from dataclasses import dataclass
import importlib.util
import re
import sys
from typing import Any, Callable, Dict, List, Tuple, Optional, Union


@dataclass
class TaskDefinition:
    """
    Defines the structure of an evolutionary task in the AlphaEvolve system.
    
    Attributes:
        problem_name: A descriptive name for the problem being solved.
        initial_code_path: Path to the user's initial Python code file or directory.
        evaluate_function_module_path: Path to the Python file containing the user's
            evaluation function.
        evaluate_function_name: Name of the user-provided evaluation function.
    """
    problem_name: str
    initial_code_path: str
    evaluate_function_module_path: str
    evaluate_function_name: str


class CodeParsingError(Exception):
    """Exception raised for errors during code parsing operations."""
    pass


class CodeParser:
    """
    Handles parsing of Python code to extract evolvable blocks marked by special comments.
    """
    
    @staticmethod
    def extract_evolvable_blocks(code_string: str) -> List[Tuple[str, str]]:
        """
        Extract code blocks marked for evolution from a Python code string.
        
        Looks for pairs of comments in the format:
        # EVOLVE-BLOCK-START <block_id>
        ... code to evolve ...
        # EVOLVE-BLOCK-END <block_id>
        
        Args:
            code_string: The full Python code as a string.
            
        Returns:
            A list of tuples containing (block_id, block_code_string) for each
            evolvable block found in the code.
            
        Raises:
            CodeParsingError: If blocks have mismatched start/end markers or other parsing issues.
        """
        # Pattern to match block start and end comments with capturing groups for block_id
        start_pattern = r'# EVOLVE-BLOCK-START\s+(\S+)'
        end_pattern = r'# EVOLVE-BLOCK-END\s+(\S+)'
        
        # Find all start markers
        start_matches = [(match.group(1), match.start()) 
                         for match in re.finditer(start_pattern, code_string)]
        
        # Find all end markers
        end_matches = [(match.group(1), match.end()) 
                       for match in re.finditer(end_pattern, code_string)]
        
        # Dictionary to store blocks by ID
        blocks: Dict[str, List[Tuple[int, int]]] = {}
        
        # Process start markers
        for block_id, start_pos in start_matches:
            if block_id not in blocks:
                blocks[block_id] = []
            # Add start position (and None as placeholder for end)
            blocks[block_id].append((start_pos, None))
        
        # Process end markers
        for block_id, end_pos in end_matches:
            if block_id not in blocks:
                raise CodeParsingError(f"Found end marker for block '{block_id}' with no matching start marker")
            
            # Find the first incomplete block for this ID
            incomplete_found = False
            for i, (start, end) in enumerate(blocks[block_id]):
                if end is None:
                    blocks[block_id][i] = (start, end_pos)
                    incomplete_found = True
                    break
            
            if not incomplete_found:
                raise CodeParsingError(f"Found extra end marker for block '{block_id}'")
        
        # Extract code blocks and verify that all blocks have matching start/end markers
        result = []
        
        for block_id, positions in blocks.items():
            for start_pos, end_pos in positions:
                if end_pos is None:
                    raise CodeParsingError(f"Block '{block_id}' has a start marker with no matching end marker")
                
                # Get lines before and after the markers to find their full line boundaries
                start_line_end = code_string.find('\n', start_pos)
                if start_line_end == -1:  # No newline found, use the end of string
                    start_line_end = len(code_string)
                
                # Find start of the line containing the end marker
                end_line_start = code_string.rfind('\n', 0, end_pos)
                if end_line_start == -1:  # No newline found, use the start of string
                    end_line_start = 0
                
                # Extract code between the markers (exclusive of the marker lines)
                block_code = code_string[start_line_end+1:end_line_start]
                
                result.append((block_id, block_code))
        
        return result


class EvaluationError(Exception):
    """Exception raised for errors during evaluation functions."""
    pass


class EvaluationWrapper:
    """
    Handles loading and running evaluation functions provided by users.
    """
    
    def load_user_evaluate_function(self, module_path: str, function_name: str) -> Callable:
        """
        Dynamically imports a user-provided evaluation function from a specified module.
        
        Args:
            module_path: Path to the Python file containing the evaluation function.
            function_name: Name of the evaluation function to load.
            
        Returns:
            The loaded function object that can be called to evaluate code.
            
        Raises:
            EvaluationError: If the module or function cannot be loaded.
        """
        try:
            # Get the absolute path to the module
            abs_module_path = module_path
            
            # Load the module from the file path
            spec = importlib.util.spec_from_file_location("user_eval_module", abs_module_path)
            if spec is None or spec.loader is None:
                raise EvaluationError(f"Failed to load module specification from {module_path}")
                
            user_module = importlib.util.module_from_spec(spec)
            sys.modules["user_eval_module"] = user_module
            spec.loader.exec_module(user_module)
            
            # Get the evaluation function from the module
            if not hasattr(user_module, function_name):
                raise EvaluationError(f"Function '{function_name}' not found in module '{module_path}'")
                
            evaluate_fn = getattr(user_module, function_name)
            if not callable(evaluate_fn):
                raise EvaluationError(f"'{function_name}' in module '{module_path}' is not callable")
                
            return evaluate_fn
            
        except ImportError as e:
            raise EvaluationError(f"Failed to import module '{module_path}': {str(e)}")
        except Exception as e:
            raise EvaluationError(f"Error loading evaluation function: {str(e)}")
    
    def run_evaluation(
        self, 
        program_module_or_string_to_test: Any, 
        user_evaluate_fn: Callable, 
        task_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Execute the user-provided evaluation function on a program.
        
        Args:
            program_module_or_string_to_test: The program to be evaluated, either as a module
                object or a string of code.
            user_evaluate_fn: The user-provided evaluation function to call.
            task_inputs: Optional dictionary of additional inputs to pass to the evaluation function.
            
        Returns:
            A dictionary mapping score names to scalar float values, e.g., {'accuracy': 0.95}.
            
        Raises:
            EvaluationError: If the evaluation function fails or returns an invalid result.
        """
        try:
            # Execute the evaluation function with the provided program and any additional inputs
            inputs = task_inputs or {}
            result = user_evaluate_fn(program_module_or_string_to_test, **inputs)
            
            # Validate that the result is a dictionary of scalar scores
            if not isinstance(result, dict):
                raise EvaluationError(
                    f"Evaluation function must return a dictionary, got {type(result).__name__}"
                )
            
            # Validate that all values are numeric
            for key, value in result.items():
                if not isinstance(value, (int, float)):
                    raise EvaluationError(
                        f"Evaluation function returned non-numeric score for '{key}': {value}"
                    )
            
            return result
            
        except Exception as e:
            # Catch any exceptions during execution of the evaluation function
            raise EvaluationError(f"Error during program evaluation: {str(e)}")