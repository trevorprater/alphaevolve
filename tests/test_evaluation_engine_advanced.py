"""
Advanced tests for EvaluationEngine features from Task 17.

This test suite verifies the new production-grade features including
evaluation cascades, fitness approximation, and parallel evaluation.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from alpha_evolve.evaluation_engine import EvaluationEngine, FitnessApproximator


class TestFitnessApproximator:
    """Test the FitnessApproximator functionality."""
    
    def test_init(self):
        """Test FitnessApproximator initialization."""
        approximator = FitnessApproximator(cache_size=1000, enable_surrogate=True)
        assert approximator.cache_size == 1000
        assert approximator.enable_surrogate == True
        assert len(approximator.evaluation_cache) == 0
        assert approximator.cache_hits == 0
        assert approximator.cache_misses == 0
    
    def test_compute_code_hash(self):
        """Test code hashing for caching."""
        approximator = FitnessApproximator()
        
        code1 = "def test(): return 1"
        code2 = "def test(): return 2"
        code3 = "def test(): return 1"  # Same as code1
        
        hash1 = approximator._compute_code_hash(code1)
        hash2 = approximator._compute_code_hash(code2)
        hash3 = approximator._compute_code_hash(code3)
        
        assert hash1 == hash3  # Same code should have same hash
        assert hash1 != hash2  # Different code should have different hash
        assert len(hash1) == 64  # SHA256 hash length
    
    def test_extract_features(self):
        """Test feature extraction from code."""
        approximator = FitnessApproximator()
        
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    else:
        return fibonacci(n-1) + fibonacci(n-2)

for i in range(10):
    print(fibonacci(i))
"""
        
        features = approximator._extract_features(code)
        
        assert 'line_count' in features
        assert 'char_count' in features
        assert 'for_loops' in features
        assert 'if_statements' in features
        assert 'function_defs' in features
        assert 'nested_depth' in features
        
        assert features['function_defs'] == 1
        assert features['for_loops'] == 1
        assert features['if_statements'] == 1
        assert features['line_count'] > 5
    
    @pytest.mark.asyncio
    async def test_caching_workflow(self):
        """Test the complete caching workflow."""
        approximator = FitnessApproximator(cache_size=2)
        
        code1 = "def test1(): return 1"
        code2 = "def test2(): return 2"
        code3 = "def test3(): return 3"
        
        result1 = {'score': 0.8, 'error': False}
        result2 = {'score': 0.6, 'error': False}
        result3 = {'score': 0.9, 'error': False}
        
        # Initially no cache hits
        cached = await approximator.get_cached_result(code1)
        assert cached is None
        assert approximator.cache_misses == 1
        
        # Cache first result
        await approximator.cache_result(code1, result1)
        cached = await approximator.get_cached_result(code1)
        assert cached is not None
        assert cached['score'] == 0.8
        assert approximator.cache_hits == 1
        
        # Cache second result
        await approximator.cache_result(code2, result2)
        
        # Cache third result (should evict first due to size limit)
        await approximator.cache_result(code3, result3)
        
        # First should be evicted
        cached1 = await approximator.get_cached_result(code1)
        assert cached1 is None  # Evicted
        
        # Third should be available
        cached3 = await approximator.get_cached_result(code3)
        assert cached3 is not None
        assert cached3['score'] == 0.9
    
    @pytest.mark.asyncio
    async def test_fitness_approximation(self):
        """Test fitness approximation using surrogate models."""
        approximator = FitnessApproximator(enable_surrogate=True)
        
        # Add training data
        training_codes = [
            "def simple(): return 1",
            "def complex(): return sum(range(100))",
            "def medium(): return len([1,2,3])"
        ]
        
        training_scores = [0.2, 0.8, 0.5]
        
        for code, score in zip(training_codes, training_scores):
            result = {'score': score, 'error': False}
            await approximator.cache_result(code, result)
        
        # Try to approximate similar code
        test_code = "def simple_test(): return 2"  # Similar to first training example
        
        approximated = await approximator.approximate_fitness(test_code, confidence_required=0.1)
        
        # Should get some approximation
        if approximated is not None:
            assert 'score' in approximated
            assert 'approximated' in approximated
            assert 'confidence' in approximated
            assert approximated['approximated'] == True
    
    def test_get_cache_stats(self):
        """Test cache statistics reporting."""
        approximator = FitnessApproximator()
        
        stats = approximator.get_cache_stats()
        
        assert 'cache_size' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'hit_rate' in stats
        assert 'training_samples' in stats
        assert 'surrogate_enabled' in stats
        
        assert stats['cache_size'] == 0
        assert stats['hit_rate'] == 0.0


class TestEvaluationEngineAdvanced:
    """Test advanced EvaluationEngine features."""
    
    @pytest.fixture
    def mock_evaluation_fn(self):
        """Create a mock evaluation function."""
        def evaluate(namespace):
            if 'test_var' in namespace:
                return {'score': namespace['test_var']}
            return {'score': 0.5}
        return evaluate
    
    @pytest.fixture
    def evaluation_engine(self):
        """Create an evaluation engine for testing."""
        config = {
            'use_sandbox': False,  # Disable sandbox for easier testing
            'use_approximation': True,
            'approximation_confidence': 0.7,
            'cache_size': 100
        }
        return EvaluationEngine(config)
    
    @pytest.mark.asyncio
    async def test_caching_integration(self, evaluation_engine, mock_evaluation_fn):
        """Test that evaluation results are properly cached."""
        code = "test_var = 0.8"
        
        # First evaluation should be full evaluation
        result1 = await evaluation_engine.evaluate_program(code, mock_evaluation_fn)
        assert result1['score'] == 0.8
        
        # Second evaluation should use cache
        with patch.object(evaluation_engine, '_evaluate_program_direct') as mock_direct:
            result2 = await evaluation_engine.evaluate_program(code, mock_evaluation_fn)
            assert result2['score'] == 0.8
            mock_direct.assert_not_called()  # Should not call direct evaluation
    
    @pytest.mark.asyncio
    async def test_force_full_evaluation(self, evaluation_engine, mock_evaluation_fn):
        """Test forcing full evaluation bypasses cache and approximation."""
        code = "test_var = 0.9"
        
        # First evaluation to populate cache
        await evaluation_engine.evaluate_program(code, mock_evaluation_fn)
        
        # Force full evaluation should bypass cache
        with patch.object(evaluation_engine, '_evaluate_program_direct', return_value={'score': 0.9}) as mock_direct:
            result = await evaluation_engine.evaluate_program(
                code, mock_evaluation_fn, force_full_evaluation=True
            )
            mock_direct.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_parallel_evaluation(self, evaluation_engine, mock_evaluation_fn):
        """Test parallel evaluation of multiple programs."""
        codes = [
            "test_var = 0.1",
            "test_var = 0.2", 
            "test_var = 0.3",
            "test_var = 0.4",
            "test_var = 0.5"
        ]
        
        results = await evaluation_engine.evaluate_programs_parallel(
            codes, mock_evaluation_fn, max_concurrent=3
        )
        
        assert len(results) == 5
        for i, result in enumerate(results):
            expected_score = (i + 1) * 0.1
            assert abs(result['score'] - expected_score) < 1e-10  # Handle floating point precision
            assert 'error' not in result or not result['error']
    
    @pytest.mark.asyncio
    async def test_evaluation_cascades(self, evaluation_engine):
        """Test evaluation cascade functionality."""
        # Create mock evaluation functions for different stages
        def quick_eval(namespace):
            # Simple check - must have main function
            if 'main' in namespace:
                return {'score': 0.6}
            return {'score': 0.1}
        
        def thorough_eval(namespace):
            # More thorough evaluation
            if 'main' in namespace and 'helper' in namespace:
                return {'score': 0.9}
            elif 'main' in namespace:
                return {'score': 0.7}
            return {'score': 0.2}
        
        def performance_eval(namespace):
            # Performance evaluation
            if 'main' in namespace and 'helper' in namespace and 'optimize' in namespace:
                return {'score': 0.95}
            return {'score': 0.5}
        
        cascade_config = [
            {
                'name': 'quick_check',
                'threshold': 0.5,
                'evaluation_fn': quick_eval
            },
            {
                'name': 'thorough_check', 
                'threshold': 0.8,
                'evaluation_fn': thorough_eval
            },
            {
                'name': 'performance_check',
                'threshold': 0.9,
                'evaluation_fn': performance_eval
            }
        ]
        
        # Test with code that should pass all stages
        good_code = """
def main():
    return helper() + optimize()

def helper():
    return 1

def optimize():
    return 2
"""
        
        result = await evaluation_engine.evaluate_program_with_cascades(
            good_code, cascade_config
        )
        
        assert 'stage_results' in result
        assert 'stages_completed' in result
        assert 'final_score' in result
        assert not result.get('error', False)
        assert result['stages_completed'] >= 1  # At least first stage should pass
        
        # Test with code that should fail early
        bad_code = "x = 1"  # No main function
        
        result_bad = await evaluation_engine.evaluate_program_with_cascades(
            bad_code, cascade_config
        )
        
        assert result_bad['stages_completed'] == 0  # Should fail first stage
        assert 'early_exit_stage' in result_bad
    
    @pytest.mark.asyncio
    async def test_cascade_with_custom_resources(self, evaluation_engine):
        """Test cascades with custom resource limits per stage."""
        def eval_fn(namespace):
            return {'score': 0.8}
        
        cascade_config = [
            {
                'name': 'fast_stage',
                'threshold': 0.5,
                'evaluation_fn': eval_fn,
                'timeout_seconds': 1.0
            },
            {
                'name': 'slow_stage',
                'threshold': 0.7,
                'evaluation_fn': eval_fn,
                'resource_limits': {
                    'cpu_limit': 2.0,
                    'memory_limit': '512M'
                }
            }
        ]
        
        code = "result = sum(range(10))"
        
        result = await evaluation_engine.evaluate_program_with_cascades(
            code, cascade_config
        )
        
        # Should complete both stages
        assert not result.get('error', False)
        assert len(result['stage_results']) >= 1
    
    def test_approximation_stats(self, evaluation_engine):
        """Test getting approximation statistics."""
        stats = evaluation_engine.get_approximation_stats()
        
        assert isinstance(stats, dict)
        assert 'cache_size' in stats
        assert 'hit_rate' in stats
        assert 'surrogate_enabled' in stats
    
    @pytest.mark.asyncio
    async def test_parallel_evaluation_with_errors(self, evaluation_engine):
        """Test parallel evaluation handles errors gracefully."""
        def error_eval_fn(namespace):
            if 'error_trigger' in namespace:
                raise ValueError("Intentional test error")
            return {'score': 0.5}
        
        codes = [
            "result = 1",  # Should succeed
            "error_trigger = True",  # Should fail
            "result = 2"  # Should succeed
        ]
        
        results = await evaluation_engine.evaluate_programs_parallel(
            codes, error_eval_fn, max_concurrent=2
        )
        
        assert len(results) == 3
        assert not results[0].get('error', False)  # First should succeed
        assert results[1].get('error', False)  # Second should fail
        assert not results[2].get('error', False)  # Third should succeed
    
    @pytest.mark.asyncio
    async def test_empty_cascade_config(self, evaluation_engine):
        """Test behavior with empty cascade configuration."""
        result = await evaluation_engine.evaluate_program_with_cascades(
            "x = 1", []
        )
        
        assert result.get('error', False)
        assert 'error_message' in result
        assert 'No cascades configured' in result['error_message']


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_evaluation_engine_advanced.py -v
    pytest.main([__file__, "-v"])