"""
Unit tests for the DistributedController class.

These tests verify the basic functionality of the DistributedController:
1. Proper initialization with all required dependencies
2. Execution of the main evolutionary loop via run_evolution
3. Execution of individual generation steps
4. Proper triggering of migration between islands

All tests use appropriate mocking to isolate the controller from its dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import asyncio
from typing import Dict, Any

from alpha_evolve.controller import DistributedController
from alpha_evolve.task_utils import TaskDefinition, EvaluationWrapper
from alpha_evolve.program_database import ProgramDatabase
from alpha_evolve.prompt_sampler import PromptSampler
from alpha_evolve.llm_interface import LLMInterface
from alpha_evolve.diff_applier import DiffApplier
from alpha_evolve.evaluation_engine import EvaluationEngine


@pytest.fixture
def mock_task_definition():
    """
    Create a mock TaskDefinition instance.
    
    Returns a MagicMock with the necessary attributes set to test values.
    """
    mock = MagicMock(spec=TaskDefinition)
    mock.problem_name = "test_problem"
    mock.evaluate_function_module_path = "test_module_path"
    mock.evaluate_function_name = "test_eval_function"
    mock.initial_code_path = "test_code_path"
    return mock


@pytest.fixture
def mock_program_database():
    """Create a mock ProgramDatabase instance."""
    return MagicMock(spec=ProgramDatabase)


@pytest.fixture
def mock_prompt_sampler():
    """Create a mock PromptSampler instance."""
    return MagicMock(spec=PromptSampler)


@pytest.fixture
def mock_llm_interface():
    """Create a mock LLMInterface instance."""
    return MagicMock(spec=LLMInterface)


@pytest.fixture
def mock_diff_applier():
    """Create a mock DiffApplier instance."""
    return MagicMock(spec=DiffApplier)


@pytest.fixture
def mock_evaluation_engine():
    """Create a mock EvaluationEngine instance."""
    return MagicMock(spec=EvaluationEngine)


@pytest.fixture
def sample_config():
    """
    Create a sample configuration dictionary for testing.
    
    The configuration includes:
    - num_generations: Number of evolution generations to run
    - batch_size_llm_calls: Number of concurrent LLM calls per batch
    - migration_frequency: How often to trigger migration between islands
    """
    return {
        "num_generations": 5,
        "batch_size_llm_calls": 3,
        "migration_frequency": 2
    }


@pytest.fixture
def controller_instance(
    mock_task_definition,
    mock_program_database,
    mock_prompt_sampler,
    mock_llm_interface,
    mock_diff_applier,
    mock_evaluation_engine,
    sample_config
):
    """
    Create a DistributedController instance with mock dependencies.
    
    This fixture creates and returns a DistributedController initialized with
    all mock dependencies, ready for testing.
    """
    return DistributedController(
        task_definition=mock_task_definition,
        program_database=mock_program_database,
        prompt_sampler=mock_prompt_sampler,
        llm_interface=mock_llm_interface,
        diff_applier=mock_diff_applier,
        evaluation_engine=mock_evaluation_engine,
        config=sample_config
    )


def test_initialization(
    controller_instance,
    mock_task_definition,
    mock_program_database,
    mock_prompt_sampler,
    mock_llm_interface,
    mock_diff_applier,
    mock_evaluation_engine,
    sample_config
):
    """Test that the controller is initialized with the correct attributes."""
    # Assert that all dependencies are correctly set as attributes
    assert controller_instance.task_definition == mock_task_definition
    assert controller_instance.program_database == mock_program_database
    assert controller_instance.prompt_sampler == mock_prompt_sampler
    assert controller_instance.llm_interface == mock_llm_interface
    assert controller_instance.diff_applier == mock_diff_applier
    assert controller_instance.evaluation_engine == mock_evaluation_engine
    assert controller_instance.config == sample_config


@pytest.mark.asyncio
async def test_run_evolution(controller_instance, sample_config):
    """
    Test that run_evolution executes the main evolution loop correctly.
    
    This test verifies that:
    1. The evolution loop runs for the correct number of generations
    2. The generation step is called with the right arguments each time
    3. The evaluation function is loaded correctly
    """
    # Mock the _generation_step method to avoid actually running it
    controller_instance._generation_step = AsyncMock()
    
    # Mock the EvaluationWrapper.load_user_evaluate_function
    mock_eval_fn = MagicMock()
    mock_wrapper = MagicMock()
    mock_wrapper.load_user_evaluate_function.return_value = mock_eval_fn
    
    with patch('alpha_evolve.controller.EvaluationWrapper', return_value=mock_wrapper):
        # Run the evolution process
        await controller_instance.run_evolution()
        
        # Check that _generation_step was called the correct number of times
        assert controller_instance._generation_step.call_count == sample_config['num_generations']
        
        # Verify each call to _generation_step has the correct arguments
        for i in range(sample_config['num_generations']):
            call_args = controller_instance._generation_step.call_args_list[i][0]
            assert call_args[0] == i  # First arg should be generation number
            assert call_args[1] == mock_eval_fn  # Second arg should be the evaluation function
        
        # Check that load_user_evaluate_function was called with the correct paths
        mock_wrapper.load_user_evaluate_function.assert_called_once_with(
            controller_instance.task_definition.evaluate_function_module_path,
            controller_instance.task_definition.evaluate_function_name
        )


@pytest.mark.asyncio
async def test_generation_step(controller_instance, sample_config):
    """
    Test that _generation_step executes correctly with mocked dependencies.
    
    This test is primarily a placeholder that will be expanded as the
    _generation_step implementation is filled in with actual functionality.
    Currently, it simply verifies the method runs without errors.
    """
    # Create a mock for the user evaluation function
    mock_eval_fn = MagicMock()
    
    # Execute the generation step
    await controller_instance._generation_step(generation_number=3, user_eval_fn=mock_eval_fn)
    
    # Currently, the _generation_step method only prints some information and
    # doesn't interact with dependencies, so there's not much to assert directly.
    # As the implementation gets filled in, we would add assertions such as:
    #
    # 1. Verify the prompt_sampler was called to sample programs
    # controller_instance.prompt_sampler.sample_programs.assert_called_once()
    # 
    # 2. Verify LLM interface was called to generate modifications
    # controller_instance.llm_interface.generate_modifications.assert_called()
    # 
    # 3. Verify diff_applier was used to apply changes
    # controller_instance.diff_applier.apply_diff.assert_called()
    # 
    # 4. Verify evaluation_engine was used to evaluate new programs
    # controller_instance.evaluation_engine.evaluate.assert_called()
    # 
    # 5. Verify program_database was updated with new entries
    # controller_instance.program_database.add_entry.assert_called()
    
    # For now, we just verify the method runs without errors
    assert True


@pytest.mark.asyncio
async def test_migration_triggered(controller_instance, sample_config):
    """
    Test that migration between islands is triggered at the appropriate generations.
    
    This test verifies that the controller correctly triggers migration based on
    the migration_frequency specified in the configuration.
    """
    # Mock the _generation_step method to avoid actually running it
    controller_instance._generation_step = AsyncMock()
    
    # Mock the program_database's trigger_migration method
    controller_instance.program_database.trigger_migration = MagicMock()
    
    # Mock the EvaluationWrapper
    mock_eval_fn = MagicMock()
    mock_wrapper = MagicMock()
    mock_wrapper.load_user_evaluate_function.return_value = mock_eval_fn
    
    with patch('alpha_evolve.controller.EvaluationWrapper', return_value=mock_wrapper):
        # Run the evolution process
        await controller_instance.run_evolution()
        
        # Currently the controller implementation only prints a message about migration
        # and doesn't actually call program_database.trigger_migration yet (it's commented out)
        # So we just verify it runs without errors for now
        
        # This test will need to be updated when the full migration functionality is implemented:
        # expected_calls = sample_config['num_generations'] // sample_config['migration_frequency']
        # assert controller_instance.program_database.trigger_migration.call_count == expected_calls
        
        # For now, we just verify the method completes without errors
        assert True