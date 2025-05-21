"""
Integration tests for the main.py script.

These tests verify that the main entry point for AlphaEvolve correctly:
1. Initializes all required components with proper configuration
2. Calls the distributed controller to run the evolution process
3. Displays the best results after evolution is complete
4. Correctly handles file paths for initial code and evaluator
5. Properly configures all component instances with appropriate parameters

The tests use mocking to isolate the main function from actual component behavior
and to verify the correct interaction flow. Each test focuses on a specific aspect
of the main function's behavior.

Tests:
- test_main_execution_flow: Verifies basic execution flow and component initialization
- test_main_no_best_program: Verifies graceful handling when no best program is found
- test_file_path_handling: Verifies correct construction and passing of file paths
- test_configuration_parameters: Verifies correct configuration values for all components

A helper context manager (mocked_gather) is provided to facilitate testing of
async code that uses asyncio.gather, making it easier to mock complex async interactions.
"""

import asyncio
import io
from contextlib import contextmanager, redirect_stdout
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alpha_evolve.controller import DistributedController
from alpha_evolve.diff_applier import DiffApplier
from alpha_evolve.evaluation_engine import EvaluationEngine
from alpha_evolve.llm_interface import LLMInterface
from alpha_evolve.main import main
from alpha_evolve.prompt_sampler import PromptSampler
from alpha_evolve.task_utils import TaskDefinition


# Context manager for mocking asyncio.gather in a maintainable way
@contextmanager
def mocked_gather(mock_results_map=None):
    """
    Context manager for mocking asyncio.gather calls in tests.

    Args:
        mock_results_map: A dictionary mapping coroutine types to result lists.
            Keys are AsyncMock instances, values are lists of results to return.

    Example:
        with mocked_gather({
            mock_llm_interface.generate_code_modification: ["result1", "result2"],
            mock_evaluation_engine.evaluate_program: [{"score": 0.9}, {"score": 0.8}]
        }):
            # Test code that uses asyncio.gather
    """
    if mock_results_map is None:
        mock_results_map = {}

    original_gather = asyncio.gather

    async def mock_gather(*args, **kwargs):
        # Check if the first arg matches any registered mocks
        if args and isinstance(args[0], AsyncMock):
            for mock_coro, results in mock_results_map.items():
                if args[0] is mock_coro:
                    return results

        # Fall back to the original gather for non-mocked cases
        try:
            return await original_gather(*args, **kwargs)
        except Exception as e:
            print(f"Error in original gather: {e}")
            return []

    # Apply the patch
    with patch("asyncio.gather", side_effect=mock_gather):
        yield


@pytest.fixture
def mock_task_definition():
    """Create a mock TaskDefinition instance."""
    mock = MagicMock(spec=TaskDefinition)
    return mock


@pytest.fixture
def mock_program_database():
    """Create a mock ProgramDatabase instance."""
    # Use spec=False to allow adding methods that may not be in the actual class yet
    mock = MagicMock(spec=False)
    # Set class attributes to make it look like ProgramDatabase
    mock.primary_score_key = "objective"
    # Mock the get_best_program method to return a program entry
    mock_program = MagicMock()
    mock_program.id = "best-program-123"
    mock_program.code = "def test(): return 84"
    mock_program.scores = {"objective": 0.95}
    mock.get_best_program = MagicMock(return_value=mock_program)
    return mock


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
def mock_controller():
    """Create a mock DistributedController instance."""
    mock = MagicMock(spec=DistributedController)
    # Set up run_evolution as AsyncMock for async testing
    mock.run_evolution = AsyncMock()
    return mock


@pytest.fixture
def mock_all_components(
    mock_task_definition,
    mock_program_database,
    mock_prompt_sampler,
    mock_llm_interface,
    mock_diff_applier,
    mock_evaluation_engine,
    mock_controller,
):
    """Set up patches for all component constructors."""
    mock_task_def_patch = patch(
        "alpha_evolve.main.TaskDefinition", return_value=mock_task_definition
    )
    mock_program_db_patch = patch(
        "alpha_evolve.main.ProgramDatabase", return_value=mock_program_database
    )
    mock_prompt_sampler_patch = patch(
        "alpha_evolve.main.PromptSampler", return_value=mock_prompt_sampler
    )
    mock_llm_interface_patch = patch(
        "alpha_evolve.main.LLMInterface", return_value=mock_llm_interface
    )
    mock_diff_applier_patch = patch(
        "alpha_evolve.main.DiffApplier", return_value=mock_diff_applier
    )
    mock_eval_engine_patch = patch(
        "alpha_evolve.main.EvaluationEngine", return_value=mock_evaluation_engine
    )
    mock_controller_patch = patch(
        "alpha_evolve.main.DistributedController", return_value=mock_controller
    )

    # Start all the patches
    mock_task_def = mock_task_def_patch.start()
    mock_program_db = mock_program_db_patch.start()
    mock_prompt_sampler_cls = mock_prompt_sampler_patch.start()
    mock_llm_interface_cls = mock_llm_interface_patch.start()
    mock_diff_applier_cls = mock_diff_applier_patch.start()
    mock_eval_engine_cls = mock_eval_engine_patch.start()
    mock_controller_cls = mock_controller_patch.start()

    yield {
        "task_definition": mock_task_definition,
        "program_database": mock_program_database,
        "prompt_sampler": mock_prompt_sampler,
        "llm_interface": mock_llm_interface,
        "diff_applier": mock_diff_applier,
        "evaluation_engine": mock_evaluation_engine,
        "controller": mock_controller,
        "task_definition_cls": mock_task_def,
        "program_database_cls": mock_program_db,
        "prompt_sampler_cls": mock_prompt_sampler_cls,
        "llm_interface_cls": mock_llm_interface_cls,
        "diff_applier_cls": mock_diff_applier_cls,
        "evaluation_engine_cls": mock_eval_engine_cls,
        "controller_cls": mock_controller_cls,
    }

    # Stop all the patches
    mock_task_def_patch.stop()
    mock_program_db_patch.stop()
    mock_prompt_sampler_patch.stop()
    mock_llm_interface_patch.stop()
    mock_diff_applier_patch.stop()
    mock_eval_engine_patch.stop()
    mock_controller_patch.stop()


@pytest.mark.asyncio
async def test_main_execution_flow(mock_all_components):
    """
    Test that the main function initializes all components and runs the evolution process.

    This test verifies:
    1. All component constructors are called with appropriate arguments
    2. The controller's run_evolution method is called
    3. The best program is retrieved from the database after evolution completes
    4. Appropriate messages are printed to stdout
    """
    # Capture stdout to verify printed messages
    stdout_capture = io.StringIO()

    # Execute the main function
    with redirect_stdout(stdout_capture):
        await main()

    # Get captured output
    output = stdout_capture.getvalue()

    # Verify all component constructors were called with appropriate arguments
    mock_all_components["task_definition_cls"].assert_called_once()
    mock_all_components["program_database_cls"].assert_called_once()
    mock_all_components["prompt_sampler_cls"].assert_called_once()
    mock_all_components["llm_interface_cls"].assert_called_once()
    mock_all_components["diff_applier_cls"].assert_called_once()
    mock_all_components["evaluation_engine_cls"].assert_called_once()
    mock_all_components["controller_cls"].assert_called_once()

    # Verify the controller's run_evolution method was called
    mock_all_components["controller"].run_evolution.assert_called_once()

    # Verify the best program was retrieved from the database
    mock_all_components["program_database"].get_best_program.assert_called_once()

    # Verify appropriate messages were printed to stdout
    assert "Starting AlphaEvolve..." in output
    assert "Evolution complete." in output
    assert "Best program found:" in output
    assert "Score: 0.95" in output  # From the mocked best program
    assert "ID: best-program-123" in output  # From the mocked best program


@pytest.mark.asyncio
async def test_main_no_best_program(mock_all_components):
    """
    Test that main handles the case where no best program is found.

    This test verifies that when program_db.get_best_program() returns None,
    the main function still completes successfully without errors.
    """
    # Configure the mock program database to return None for get_best_program()
    mock_all_components["program_database"].get_best_program.return_value = None

    # Capture stdout to verify printed messages
    stdout_capture = io.StringIO()

    # Execute the main function
    with redirect_stdout(stdout_capture):
        await main()

    # Get captured output
    output = stdout_capture.getvalue()

    # Verify controller's run_evolution was called
    mock_all_components["controller"].run_evolution.assert_called_once()

    # Verify program_database.get_best_program was called
    mock_all_components["program_database"].get_best_program.assert_called_once()

    # Verify expected output messages
    assert "Starting AlphaEvolve..." in output
    assert "Evolution complete." in output
    # Verify that best program information is NOT printed
    assert "Best program found:" not in output


@pytest.mark.asyncio
async def test_file_path_handling(mock_all_components):
    """
    Test that main correctly constructs file paths for initial_code.py and evaluator.py.

    This test verifies:
    1. The base directory is correctly determined using Path and __file__
    2. The initial_code_path and evaluator_path are correctly constructed
    3. These paths are passed to TaskDefinition
    """
    # Create a mock Path object to track how it's used
    mock_base_dir = MagicMock()
    mock_initial_code_path = MagicMock()
    mock_evaluator_path = MagicMock()

    # Configure the mock Path behavior
    def mock_path_div(self, other):
        if other == "initial_code.py":
            return mock_initial_code_path
        elif other == "evaluator.py":
            return mock_evaluator_path
        return MagicMock()

    mock_base_dir.__truediv__ = mock_path_div
    mock_initial_code_path.__str__ = MagicMock(
        return_value="/mocked/path/to/initial_code.py"
    )
    mock_evaluator_path.__str__ = MagicMock(return_value="/mocked/path/to/evaluator.py")

    # Set up the patch for Path(os.path.dirname(os.path.dirname(__file__)))
    with patch("alpha_evolve.main.Path", return_value=mock_base_dir):
        # Execute the main function
        await main()

        # The TaskDefinition should be constructed with these file paths
        # We need to extract the call arguments
        call_args = mock_all_components["task_definition_cls"].call_args[1]

        # Verify initial_code_path and evaluator_path were passed to TaskDefinition
        assert "initial_code_path" in call_args
        assert "evaluate_function_module_path" in call_args

        # Verify the values were string representations of the mocked Path objects
        assert call_args["initial_code_path"] == str(mock_initial_code_path)
        assert call_args["evaluate_function_module_path"] == str(mock_evaluator_path)


@pytest.mark.asyncio
async def test_configuration_parameters(mock_all_components):
    """
    Test that main correctly configures all components with the expected parameters.

    This test verifies:
    1. The correct configuration parameters are passed to ProgramDatabase
    2. The correct configuration parameters are passed to DistributedController
    3. Feature dimension bins are correctly defined
    """
    # Execute the main function
    await main()

    # Verify ProgramDatabase was constructed with correct parameters
    program_db_call_args = mock_all_components["program_database_cls"].call_args[1]
    assert "feature_dimensions_bins" in program_db_call_args
    assert "primary_score_key" in program_db_call_args

    # Verify feature_dimensions_bins is a list of lists with correct structure
    feature_bins = program_db_call_args["feature_dimensions_bins"]
    assert isinstance(feature_bins, list)
    assert (
        len(feature_bins) == 2
    )  # Two feature dimensions: code_length and objective_score

    # Verify specific bin values
    # First list should be code_length bins
    assert feature_bins[0] == [0, 50, 100, 1000]
    # Second list should be objective_score bins
    assert feature_bins[1][0] == -float("inf")  # First bin starts at -infinity
    assert feature_bins[1][3] == 1.0  # Last bin ends at 1.0

    # Verify primary_score_key
    assert program_db_call_args["primary_score_key"] == "objective"

    # Verify DistributedController was constructed with correct parameters
    controller_call_args = mock_all_components["controller_cls"].call_args[1]

    # Verify all required components are passed to the controller
    assert "task_definition" in controller_call_args
    assert "program_database" in controller_call_args
    assert "prompt_sampler" in controller_call_args
    assert "llm_interface" in controller_call_args
    assert "diff_applier" in controller_call_args
    assert "evaluation_engine" in controller_call_args
    assert "config" in controller_call_args

    # Verify configuration values in the config dictionary
    config = controller_call_args["config"]
    assert config["num_generations"] == 3
    assert config["batch_size_new_programs"] == 2
    assert config["primary_score_key"] == "objective"
    assert config["num_parents"] == 1
    assert config["num_inspirations"] == 1
    assert config["llm_type"] == "pro"
    assert config["output_format"] == "diff"
    assert config["migration_frequency"] == 2

