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
import hashlib
import json
import time
from typing import Any, Callable, Dict, Optional, Union, List, Tuple
from pathlib import Path
import os
import logging
from dataclasses import dataclass
from collections import defaultdict
import pickle

from alpha_evolve.task_utils import EvaluationWrapper, EvaluationError
from alpha_evolve.sandbox import create_sandbox, ResourceLimits, SandboxError
from alpha_evolve.config import get_config


@dataclass
class ApproximationModel:
    """Simple approximation model for fitness estimation."""
    model_type: str
    features: List[str]
    accuracy: float
    sample_count: int
    last_updated: float


class FitnessApproximator:
    """
    Manages fitness approximation for expensive evaluations.
    
    This class implements various strategies for approximating fitness without
    running full evaluations, including caching, surrogate models, and sampling.
    """
    
    def __init__(self, cache_size: int = 10000, enable_surrogate: bool = True):
        """
        Initialize the fitness approximator.
        
        Args:
            cache_size: Maximum number of cached evaluation results
            enable_surrogate: Whether to use surrogate models for approximation
        """
        self.cache_size = cache_size
        self.enable_surrogate = enable_surrogate
        self.evaluation_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        self.logger = logging.getLogger(__name__ + ".FitnessApproximator")
        
        # Surrogate model storage
        self.surrogate_models = {}
        self.training_data = defaultdict(list)
        
        # Adaptive sampling parameters
        self.sample_history = []
        self.confidence_threshold = 0.8
        
    def _compute_code_hash(self, program_code: str, task_inputs: Optional[Dict[str, Any]] = None) -> str:
        """Compute a hash of the program code and task inputs for caching."""
        # Include task_inputs in the hash to ensure different inputs produce different cache keys
        cache_data = {
            'code': program_code,
            'inputs': task_inputs or {}
        }
        # Convert to JSON string for consistent hashing
        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_string.encode()).hexdigest()
    
    def _extract_features(self, program_code: str) -> Dict[str, float]:
        """
        Extract features from program code for surrogate modeling.
        
        Args:
            program_code: The Python code to analyze
            
        Returns:
            Dictionary of feature name to value mappings
        """
        features = {}
        
        # Basic code metrics
        lines = program_code.split('\n')
        features['line_count'] = len(lines)
        features['char_count'] = len(program_code)
        features['avg_line_length'] = sum(len(line) for line in lines) / max(len(lines), 1)
        
        # Count various Python constructs
        features['for_loops'] = program_code.count('for ')
        features['while_loops'] = program_code.count('while ')
        features['if_statements'] = program_code.count('if ')
        features['function_defs'] = program_code.count('def ')
        features['class_defs'] = program_code.count('class ')
        features['imports'] = program_code.count('import ')
        features['try_blocks'] = program_code.count('try:')
        
        # Complexity indicators
        features['nested_depth'] = self._estimate_nesting_depth(program_code)
        features['unique_vars'] = len(set(self._extract_variable_names(program_code)))
        
        return features
    
    def _estimate_nesting_depth(self, code: str) -> float:
        """Estimate the maximum nesting depth in the code."""
        max_depth = 0
        current_depth = 0
        
        for line in code.split('\n'):
            stripped = line.lstrip()
            if stripped and not stripped.startswith('#'):
                # Count leading whitespace
                indent = len(line) - len(line.lstrip())
                # Estimate depth (assuming 4-space indentation)
                depth = indent // 4
                max_depth = max(max_depth, depth)
        
        return float(max_depth)
    
    def _extract_variable_names(self, code: str) -> List[str]:
        """Extract variable names from code (simplified heuristic)."""
        import re
        # Simple regex to find potential variable assignments
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*='
        variables = re.findall(pattern, code)
        return [var for var in variables if var not in ['def', 'class', 'if', 'for', 'while']]
    
    async def get_cached_result(self, program_code: str, task_inputs: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, float]]:
        """
        Check if we have a cached result for this program code and task inputs.
        
        Args:
            program_code: The Python code to check
            task_inputs: Optional task inputs that affect evaluation
            
        Returns:
            Cached evaluation result or None if not found
        """
        code_hash = self._compute_code_hash(program_code, task_inputs)
        
        if code_hash in self.evaluation_cache:
            self.cache_hits += 1
            cached_result = self.evaluation_cache[code_hash]
            self.logger.debug(f"Cache hit for code hash {code_hash[:8]}...")
            return cached_result.copy()
        
        self.cache_misses += 1
        return None
    
    async def cache_result(self, program_code: str, result: Dict[str, float], task_inputs: Optional[Dict[str, Any]] = None) -> None:
        """
        Cache an evaluation result.
        
        Args:
            program_code: The Python code that was evaluated
            result: The evaluation result to cache
            task_inputs: Optional task inputs that were used for evaluation
        """
        code_hash = self._compute_code_hash(program_code, task_inputs)
        
        # Implement LRU cache behavior
        if len(self.evaluation_cache) >= self.cache_size:
            # Remove oldest entry (simplified - in production use proper LRU)
            oldest_key = next(iter(self.evaluation_cache))
            del self.evaluation_cache[oldest_key]
        
        self.evaluation_cache[code_hash] = result.copy()
        self.logger.debug(f"Cached result for code hash {code_hash[:8]}...")
        
        # Update training data for surrogate models
        if self.enable_surrogate and not result.get('error', False):
            features = self._extract_features(program_code)
            score = result.get('score', float('-inf'))
            self.training_data['default'].append((features, score))
    
    async def approximate_fitness(self, program_code: str, confidence_required: float = 0.7) -> Optional[Dict[str, float]]:
        """
        Approximate fitness using available surrogate models.
        
        Args:
            program_code: The Python code to approximate fitness for
            confidence_required: Minimum confidence required for approximation
            
        Returns:
            Approximated fitness result or None if confidence too low
        """
        if not self.enable_surrogate:
            return None
        
        # Check if we have enough training data
        if len(self.training_data['default']) < 10:
            self.logger.debug("Insufficient training data for approximation")
            return None
        
        features = self._extract_features(program_code)
        
        # Simple k-nearest neighbors approximation
        try:
            prediction, confidence = self._knn_predict(features, k=5)
            
            if confidence >= confidence_required:
                self.logger.info(f"Fitness approximated: {prediction:.4f} (confidence: {confidence:.3f})")
                return {
                    'score': prediction,
                    'approximated': True,
                    'confidence': confidence,
                    'method': 'knn'
                }
            else:
                self.logger.debug(f"Approximation confidence too low: {confidence:.3f} < {confidence_required}")
                return None
                
        except Exception as e:
            self.logger.warning(f"Fitness approximation failed: {e}")
            return None
    
    def _knn_predict(self, features: Dict[str, float], k: int = 5) -> Tuple[float, float]:
        """
        K-nearest neighbors prediction for fitness approximation.
        
        Args:
            features: Feature vector for the program
            k: Number of neighbors to consider
            
        Returns:
            Tuple of (predicted_score, confidence)
        """
        training_points = self.training_data['default']
        
        if len(training_points) < k:
            k = len(training_points)
        
        # Calculate distances to all training points
        distances = []
        for train_features, train_score in training_points:
            # Simple Euclidean distance
            distance = 0.0
            common_features = set(features.keys()) & set(train_features.keys())
            
            for feature in common_features:
                diff = features[feature] - train_features[feature]
                distance += diff * diff
            
            distance = distance ** 0.5
            distances.append((distance, train_score))
        
        # Sort by distance and take k nearest
        distances.sort(key=lambda x: x[0])
        nearest = distances[:k]
        
        # Predict as weighted average
        total_weight = 0.0
        weighted_sum = 0.0
        
        for distance, score in nearest:
            # Use inverse distance weighting (add small epsilon to avoid division by zero)
            weight = 1.0 / (distance + 1e-6)
            weighted_sum += weight * score
            total_weight += weight
        
        prediction = weighted_sum / total_weight if total_weight > 0 else 0.0
        
        # Calculate confidence based on agreement of nearest neighbors
        scores = [score for _, score in nearest]
        if len(scores) > 1:
            score_std = (sum((s - prediction) ** 2 for s in scores) / len(scores)) ** 0.5
            # Convert std to confidence (lower std = higher confidence)
            confidence = max(0.0, 1.0 - score_std / max(abs(prediction), 1.0))
        else:
            confidence = 0.5
        
        return prediction, confidence
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'cache_size': len(self.evaluation_cache),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate': hit_rate,
            'training_samples': len(self.training_data['default']),
            'surrogate_enabled': self.enable_surrogate
        }


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
            
            # Fitness approximation settings
            self.use_approximation = evaluation_config.get('use_approximation', True)
            self.approximation_confidence = evaluation_config.get('approximation_confidence', 0.7)
            cache_size = evaluation_config.get('cache_size', 10000)
            
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
            
            # Fitness approximation settings from global config
            self.use_approximation = config.evaluation.use_approximation
            self.approximation_confidence = config.evaluation.approximation_confidence
            cache_size = config.evaluation.cache_size
            
            # Create resource limits from global config
            self.resource_limits = ResourceLimits(
                cpu_limit=config.sandbox.cpu_limit,
                memory_limit=config.sandbox.memory_limit,
                timeout_seconds=config.sandbox.timeout_seconds,
                max_output_size=config.sandbox.max_output_size,
                network_disabled=config.sandbox.network_disabled
            )
        
        # Initialize fitness approximator
        self.fitness_approximator = FitnessApproximator(
            cache_size=cache_size,
            enable_surrogate=self.use_approximation
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
        task_inputs: Optional[Dict[str, Any]] = None,
        force_full_evaluation: bool = False
    ) -> Dict[str, float]:
        """
        Evaluate a program code string using the provided evaluation function.
        
        This method first checks for cached results, then attempts fitness approximation
        if enabled, and finally performs full evaluation if needed.
        
        Args:
            program_code_string: The Python code to evaluate as a string.
            user_evaluate_fn: The user-provided function that will evaluate the code.
            task_inputs: Optional dictionary of additional inputs for the evaluation function.
            force_full_evaluation: If True, skip caching and approximation.
            
        Returns:
            A dictionary mapping score names to float values. If an error occurs,
            returns a dictionary with 'error' set to True and 'score' set to negative infinity.
        """
        try:
            # Step 1: Check cache if not forcing full evaluation
            if not force_full_evaluation:
                cached_result = await self.fitness_approximator.get_cached_result(program_code_string, task_inputs)
                if cached_result is not None:
                    self.logger.debug("Using cached evaluation result")
                    return cached_result
            
            # Step 2: Try fitness approximation if enabled and not forcing full evaluation
            if not force_full_evaluation and self.use_approximation:
                approximated_result = await self.fitness_approximator.approximate_fitness(
                    program_code_string, self.approximation_confidence
                )
                if approximated_result is not None:
                    self.logger.debug("Using approximated fitness result")
                    return approximated_result
            
            # Step 3: Perform full evaluation
            self.logger.debug("Performing full evaluation")
            if self.use_sandbox and self.sandbox:
                result = await self._evaluate_program_sandboxed(
                    program_code_string, user_evaluate_fn, task_inputs
                )
            else:
                result = await self._evaluate_program_direct(
                    program_code_string, user_evaluate_fn, task_inputs
                )
            
            # Step 4: Cache the result
            await self.fitness_approximator.cache_result(program_code_string, result, task_inputs)
            
            return result
                
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
    
    async def evaluate_program_with_cascades(
        self,
        program_code_string: str,
        cascade_config: list,
        task_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, float]:
        """
        Evaluate a program using a multi-stage cascade evaluation pipeline.
        
        This method applies a series of increasingly complex evaluations, where each
        stage must pass a threshold before proceeding to the next stage. This allows
        for efficient early filtering of poor solutions.
        
        Args:
            program_code_string: The Python code to evaluate as a string.
            cascade_config: List of cascade stage configurations.
            task_inputs: Optional dictionary of additional inputs for evaluation functions.
            
        Returns:
            A dictionary containing cascade evaluation results.
        """
        try:
            return await self._apply_evaluation_cascades(program_code_string, cascade_config)
        except Exception as e:
            self.logger.error(f"Error in cascade evaluation: {e}")
            return {
                'error': True,
                'score': float('-inf'),
                'error_type': type(e).__name__,
                'error_message': str(e),
                'stages_completed': 0,
                'stage_results': []
            }
    
    async def evaluate_programs_parallel(
        self,
        program_code_list: List[str],
        user_evaluate_fn: Callable,
        task_inputs: Optional[Dict[str, Any]] = None,
        max_concurrent: int = 5
    ) -> List[Dict[str, float]]:
        """
        Evaluate multiple programs in parallel.
        
        Args:
            program_code_list: List of Python code strings to evaluate
            user_evaluate_fn: The user-provided function that will evaluate the code
            task_inputs: Optional dictionary of additional inputs for the evaluation function
            max_concurrent: Maximum number of concurrent evaluations
            
        Returns:
            List of evaluation results in the same order as input programs
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def evaluate_with_semaphore(program_code: str) -> Dict[str, float]:
            async with semaphore:
                return await self.evaluate_program(program_code, user_evaluate_fn, task_inputs)
        
        self.logger.info(f"Starting parallel evaluation of {len(program_code_list)} programs (max_concurrent={max_concurrent})")
        
        # Create tasks for all evaluations
        tasks = [evaluate_with_semaphore(code) for code in program_code_list]
        
        # Wait for all evaluations to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Parallel evaluation {i} failed: {result}")
                processed_results.append({
                    'error': True,
                    'score': float('-inf'),
                    'error_type': type(result).__name__,
                    'error_message': str(result)
                })
            else:
                processed_results.append(result)
        
        self.logger.info(f"Completed parallel evaluation of {len(program_code_list)} programs")
        return processed_results
    
    def get_approximation_stats(self) -> Dict[str, Any]:
        """Get fitness approximation performance statistics."""
        return self.fitness_approximator.get_cache_stats()
    
    def cleanup(self) -> None:
        """Clean up sandbox resources."""
        if self.sandbox:
            self.sandbox.cleanup()
    
    async def _apply_evaluation_cascades(self, program_code_string: str, cascades: list) -> Dict[str, float]:
        """
        Apply a series of increasingly complex evaluations to a program.
        
        This implements a multi-stage evaluation pipeline where each stage can have
        different thresholds, resource limits, and evaluation functions. Stages run
        sequentially, and later stages only execute if earlier stages pass.
        
        Args:
            program_code_string: The Python code to evaluate as a string.
            cascades: A list of evaluation stage configurations. Each stage should contain:
                - 'threshold': Minimum score required to proceed to next stage
                - 'evaluation_fn': Function to use for this stage
                - 'resource_limits': Optional custom resource limits for this stage
                - 'timeout_seconds': Optional timeout for this stage
                - 'inputs': Optional inputs specific to this stage
                - 'name': Optional name for the stage (for logging)
            
        Returns:
            A dictionary containing the evaluation results with stage-specific information.
        """
        if not cascades:
            self.logger.warning("No cascades provided to _apply_evaluation_cascades")
            return {'error': True, 'score': float('-inf'), 'error_message': 'No cascades configured'}
        
        cascade_results = {
            'stage_results': [],
            'stages_completed': 0,
            'final_score': float('-inf'),
            'error': False,
            'early_exit_stage': None
        }
        
        for stage_idx, stage_config in enumerate(cascades):
            stage_name = stage_config.get('name', f'stage_{stage_idx + 1}')
            evaluation_fn = stage_config.get('evaluation_fn')
            threshold = stage_config.get('threshold', 0.0)
            stage_inputs = stage_config.get('inputs', {})
            
            if not evaluation_fn:
                self.logger.error(f"No evaluation function provided for {stage_name}")
                cascade_results['error'] = True
                cascade_results['error_message'] = f"No evaluation function for {stage_name}"
                break
            
            self.logger.info(f"Running evaluation cascade {stage_name} (threshold: {threshold})")
            
            # Create temporary engine with stage-specific settings if provided
            stage_engine = self
            if 'resource_limits' in stage_config or 'timeout_seconds' in stage_config:
                stage_eval_config = {
                    'use_sandbox': self.use_sandbox,
                    'sandbox_type': self.sandbox_type,
                    'cpu_limit': stage_config.get('resource_limits', {}).get('cpu_limit', self.resource_limits.cpu_limit),
                    'memory_limit': stage_config.get('resource_limits', {}).get('memory_limit', self.resource_limits.memory_limit),
                    'timeout_seconds': stage_config.get('timeout_seconds', self.resource_limits.timeout_seconds),
                    'max_output_size': stage_config.get('resource_limits', {}).get('max_output_size', self.resource_limits.max_output_size),
                    'network_disabled': stage_config.get('resource_limits', {}).get('network_disabled', self.resource_limits.network_disabled)
                }
                stage_engine = EvaluationEngine(stage_eval_config)
            
            try:
                # Run evaluation for this stage
                stage_result = await stage_engine.evaluate_program(
                    program_code_string, evaluation_fn, stage_inputs
                )
                
                stage_info = {
                    'stage_name': stage_name,
                    'stage_index': stage_idx,
                    'threshold': threshold,
                    'result': stage_result,
                    'passed': False
                }
                
                # Check if stage passed
                if stage_result.get('error', False):
                    stage_info['passed'] = False
                    cascade_results['stage_results'].append(stage_info)
                    cascade_results['error'] = True
                    cascade_results['error_message'] = f"Stage {stage_name} failed: {stage_result.get('error_message', 'Unknown error')}"
                    cascade_results['early_exit_stage'] = stage_name
                    self.logger.warning(f"Stage {stage_name} failed with error: {stage_result.get('error_message')}")
                    break
                
                stage_score = stage_result.get('score', float('-inf'))
                if stage_score >= threshold:
                    stage_info['passed'] = True
                    cascade_results['stages_completed'] += 1
                    cascade_results['final_score'] = stage_score
                    self.logger.info(f"Stage {stage_name} passed with score {stage_score:.4f} (>= {threshold})")
                else:
                    stage_info['passed'] = False
                    cascade_results['early_exit_stage'] = stage_name
                    self.logger.info(f"Stage {stage_name} failed threshold with score {stage_score:.4f} (< {threshold})")
                
                cascade_results['stage_results'].append(stage_info)
                
                # If stage didn't pass threshold, stop cascade
                if not stage_info['passed']:
                    break
                    
            except Exception as e:
                self.logger.error(f"Unexpected error in stage {stage_name}: {e}")
                stage_info = {
                    'stage_name': stage_name,
                    'stage_index': stage_idx,
                    'threshold': threshold,
                    'result': {'error': True, 'error_message': str(e)},
                    'passed': False
                }
                cascade_results['stage_results'].append(stage_info)
                cascade_results['error'] = True
                cascade_results['error_message'] = f"Stage {stage_name} exception: {str(e)}"
                cascade_results['early_exit_stage'] = stage_name
                break
            
            finally:
                # Clean up temporary engine if created
                if stage_engine != self:
                    stage_engine.cleanup()
        
        # If all stages completed successfully, mark as successful
        if cascade_results['stages_completed'] == len(cascades) and not cascade_results['error']:
            self.logger.info(f"All {len(cascades)} cascade stages completed successfully")
        
        return cascade_results
    
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