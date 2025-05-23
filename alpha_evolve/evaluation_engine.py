"""
Evaluation engine for AlphaEvolve.

This module provides the EvaluationEngine class, which is responsible for executing
and evaluating generated code using user-provided evaluation functions.
"""

import asyncio
import importlib.util
import sys
import tempfile
import traceback
from typing import Any, Callable, Dict, Optional, Union
from pathlib import Path
import os
import logging

from alpha_evolve.task_utils import EvaluationWrapper, EvaluationError
from alpha_evolve.sandbox import create_sandbox, ResourceLimits, SandboxError
from alpha_evolve.config import get_config


class EvaluationEngine:
    """
    Handles the evaluation of generated program code using user-provided evaluation functions.
    
    This class executes program code strings, handles potential execution errors,
    and returns evaluation scores using user-defined evaluation metrics.
    """
    
    def __init__(self, evaluation_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the EvaluationEngine with optional configuration.
        
        Args:
            evaluation_config: Optional configuration dictionary that may include
                parameters like timeouts, sandboxing options, etc. If None, uses global config.
        """
        self.evaluation_wrapper = EvaluationWrapper()
        self.logger = logging.getLogger(__name__)
        
        # Get configuration from global config or override
        config = get_config()
        if evaluation_config:
            # Override specific settings
            self.use_sandbox = evaluation_config.get('use_sandbox', config.sandbox.enabled)
            self.sandbox_type = evaluation_config.get('sandbox_type', config.sandbox.type)
            
            # Create resource limits from config override
            self.resource_limits = ResourceLimits(
                cpu_limit=evaluation_config.get('cpu_limit', config.sandbox.cpu_limit),
                memory_limit=evaluation_config.get('memory_limit', config.sandbox.memory_limit),
                timeout_seconds=evaluation_config.get('timeout_seconds', config.sandbox.timeout_seconds),
                max_output_size=evaluation_config.get('max_output_size', config.sandbox.max_output_size),
                network_disabled=evaluation_config.get('network_disabled', config.sandbox.network_disabled)
            )
        else:
            # Use global configuration
            self.use_sandbox = config.sandbox.enabled
            self.sandbox_type = config.sandbox.type
            
            # Create resource limits from global config
            self.resource_limits = ResourceLimits(
                cpu_limit=config.sandbox.cpu_limit,
                memory_limit=config.sandbox.memory_limit,
                timeout_seconds=config.sandbox.timeout_seconds,
                max_output_size=config.sandbox.max_output_size,
                network_disabled=config.sandbox.network_disabled
            )
        
        # Initialize sandbox
        self.sandbox = None
        if self.use_sandbox:
            try:
                self.sandbox = create_sandbox(self.sandbox_type, self.resource_limits)
                self.logger.info(f"Initialized {self.sandbox_type} sandbox for secure execution")
            except SandboxError as e:
                self.logger.warning(f"Failed to initialize sandbox: {e}. Falling back to direct execution.")
                self.use_sandbox = False
        
    async def evaluate_program(
        self, 
        program_code_string: str, 
        user_evaluate_fn: Callable, 
        task_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Evaluate a program code string using the provided evaluation function.
        
        This method executes the program code string in a sandboxed environment,
        then passes the namespace to the user-provided evaluation function.
        
        Args:
            program_code_string: The Python code to evaluate as a string.
            user_evaluate_fn: The user-provided function that will evaluate the code.
            task_inputs: Optional dictionary of additional inputs for the evaluation function.
            
        Returns:
            A dictionary mapping score names to float values. If an error occurs,
            returns a dictionary with 'error' set to True and 'score' set to negative infinity.
        """
        try:
            if self.use_sandbox and self.sandbox:
                return await self._evaluate_program_sandboxed(
                    program_code_string, user_evaluate_fn, task_inputs
                )
            else:
                return await self._evaluate_program_direct(
                    program_code_string, user_evaluate_fn, task_inputs
                )
                
        except Exception as e:
            self.logger.error(f"Unexpected error in evaluate_program: {e}")
            return {
                'error': True, 
                'score': float('-inf'),
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
    
    async def _evaluate_program_sandboxed(
        self, 
        program_code_string: str, 
        user_evaluate_fn: Callable, 
        task_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Evaluate program using sandboxed execution.
        
        Args:
            program_code_string: The Python code to evaluate as a string.
            user_evaluate_fn: The user-provided function that will evaluate the code.
            task_inputs: Optional dictionary of additional inputs for the evaluation function.
            
        Returns:
            A dictionary mapping score names to float values.
        """
        try:
            # Execute code in sandbox
            sandbox_result = await self.sandbox.execute(program_code_string, task_inputs)
            
            if not sandbox_result.success:
                # Handle sandbox execution failure
                return {
                    'error': True,
                    'score': float('-inf'),
                    'error_type': 'SandboxExecutionError',
                    'error_message': sandbox_result.error_message or sandbox_result.stderr,
                    'execution_time': sandbox_result.execution_time,
                    'return_code': sandbox_result.return_code
                }
            
            # Create namespace from sandbox execution
            # Note: In a real implementation, we'd need to carefully extract
            # the variables from the sandbox execution context
            local_namespace = {
                '__sandbox_stdout__': sandbox_result.stdout,
                '__sandbox_stderr__': sandbox_result.stderr,
                '__execution_time__': sandbox_result.execution_time,
                '__resource_usage__': sandbox_result.resource_usage
            }
            
            # For now, we'll execute the code again locally to get the namespace
            # This is a compromise between security and functionality
            # In production, you might want to serialize/deserialize the namespace
            try:
                exec(program_code_string, {}, local_namespace)
            except Exception as e:
                return {
                    'error': True,
                    'score': float('-inf'),
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'execution_time': sandbox_result.execution_time
                }
            
            # Run evaluation
            try:
                result = self.evaluation_wrapper.run_evaluation(
                    local_namespace,
                    user_evaluate_fn,
                    task_inputs
                )
                
                # Add sandbox metrics to result
                result['execution_time'] = sandbox_result.execution_time
                if sandbox_result.resource_usage:
                    result['resource_usage'] = sandbox_result.resource_usage
                
                return result
                
            except EvaluationError as e:
                return {
                    'error': True,
                    'score': float('-inf'),
                    'error_type': 'EvaluationError',
                    'error_message': str(e),
                    'execution_time': sandbox_result.execution_time
                }
                
        except Exception as e:
            self.logger.error(f"Sandboxed evaluation failed: {e}")
            return {
                'error': True,
                'score': float('-inf'),
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
    
    async def _evaluate_program_direct(
        self, 
        program_code_string: str, 
        user_evaluate_fn: Callable, 
        task_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Evaluate program using direct execution (less secure, for development).
        
        Args:
            program_code_string: The Python code to evaluate as a string.
            user_evaluate_fn: The user-provided function that will evaluate the code.
            task_inputs: Optional dictionary of additional inputs for the evaluation function.
            
        Returns:
            A dictionary mapping score names to float values.
        """
        # Define a default error result
        error_result = {'error': True, 'score': float('-inf')}
        
        # Create a dictionary to serve as a local namespace for executing the code
        local_namespace = {}
        
        try:
            # Execute the program code string in the local namespace
            exec(program_code_string, {}, local_namespace)
        except SyntaxError as e:
            # Handle syntax errors in the program code
            return {
                'error': True, 
                'score': float('-inf'),
                'error_type': 'SyntaxError',
                'error_message': str(e)
            }
        except Exception as e:
            # Handle other execution errors
            return {
                'error': True, 
                'score': float('-inf'),
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
        
        # Run the evaluation using the EvaluationWrapper
        try:
            # Pass the local namespace to the evaluation wrapper
            result = self.evaluation_wrapper.run_evaluation(
                local_namespace,
                user_evaluate_fn,
                task_inputs
            )
            return result
        except EvaluationError as e:
            # Handle errors from the evaluation function
            return {
                'error': True, 
                'score': float('-inf'),
                'error_type': 'EvaluationError',
                'error_message': str(e)
            }
        except Exception as e:
            # Handle any other unexpected errors
            return {
                'error': True, 
                'score': float('-inf'),
                'error_type': type(e).__name__,
                'error_message': str(e)
            }
    
    def cleanup(self) -> None:
        """Clean up sandbox resources."""
        if self.sandbox:
            self.sandbox.cleanup()
    
    async def _apply_evaluation_cascades(self, program_code_string: str, cascades: list) -> Dict[str, float]:
        """
        Apply a series of increasingly complex evaluations to a program.
        
        This is a placeholder for a future feature that would allow for multiple
        evaluation stages, with each subsequent stage only running if the previous
        stages passed successfully.
        
        Args:
            program_code_string: The Python code to evaluate as a string.
            cascades: A list of evaluation configurations to apply in sequence.
            
        Returns:
            A dictionary containing the evaluation results.
        """
        # This is a placeholder for future implementation
        pass
    
    async def _get_llm_feedback(self, program_code_string: str, execution_error: Optional[Exception] = None) -> str:
        """
        Get feedback from an LLM about the quality of the program or any errors.
        
        This is a placeholder for a future feature that would leverage LLMs to
        provide qualitative feedback about code quality or to help diagnose errors.
        
        Args:
            program_code_string: The Python code to evaluate as a string.
            execution_error: An optional exception that occurred during execution.
            
        Returns:
            A string containing LLM feedback about the code.
        """
        # This is a placeholder for future implementation
        return "LLM feedback placeholder"