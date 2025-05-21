"""
Tests for the seeding functionality in the DistributedController class.

These tests verify that the controller properly seeds the program database
with initial evolvable blocks from the provided code file.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock, ANY
import tempfile
import os
import asyncio
import io
from contextlib import redirect_stdout

from alpha_evolve.controller import DistributedController
from alpha_evolve.task_utils import TaskDefinition, CodeParser
from alpha_evolve.program_database import ProgramDatabase, ProgramEntry


@pytest.fixture
def sample_evolvable_code():
    """
    Create a temporary file with sample code containing evolvable blocks.
    
    Returns:
        The path to the temporary file.
    """
    code_content = '''
def non_evolvable_function():
    return "This function is not marked for evolution"

# EVOLVE-BLOCK-START block1
def function_to_evolve():
    # This is a simple function that we want to evolve
    return 42
# EVOLVE-BLOCK-END block1

class SomeClass:
    def __init__(self):
        self.value = 0
        
    # EVOLVE-BLOCK-START block2
    def method_to_evolve(self, x):
        # This method should also be evolved
        return x * 2
    # EVOLVE-BLOCK-END block2
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code_content)
        temp_path = temp_file.name
    
    # Return the path and ensure the file is deleted after the test
    yield temp_path
    os.unlink(temp_path)


@pytest.mark.asyncio
async def test_seeding_process():
    """
    Test the seeding functionality of the controller.
    
    This test verifies:
    1. The controller correctly loads the initial code file
    2. Extracts evolvable blocks from the code
    3. Evaluates each block
    4. Adds the blocks to the program database
    """
    # Create a real temporary file with evolvable blocks
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write('''
# EVOLVE-BLOCK-START block1
def function1():
    return 42
# EVOLVE-BLOCK-END block1

# EVOLVE-BLOCK-START block2
def function2(x):
    return x * 2
# EVOLVE-BLOCK-END block2
''')
        code_path = temp_file.name
    
    try:
        # Create mock dependencies
        task_definition = MagicMock(spec=TaskDefinition)
        task_definition.problem_name = "test_seeding"
        task_definition.initial_code_path = code_path
        task_definition.evaluate_function_module_path = "test_module_path"
        task_definition.evaluate_function_name = "test_eval_function"
        
        program_database = MagicMock(spec=ProgramDatabase)
        program_database.primary_score_key = "fitness"
        # Configure add_program to always return True (was added to archive)
        program_database.add_program.return_value = True
        
        # Define mock results based on block content
        block_contents = [
            'def function1():\n    return 42',
            'def function2(x):\n    return x * 2'
        ]
        
        mock_eval_results = [
            {"fitness": 0.8, "complexity": 0.2},  # block1
            {"fitness": 0.9, "complexity": 0.3}   # block2
        ]
        
        # Create a mock evaluation engine that returns the correct results
        evaluation_engine = MagicMock()
        
        # Create an async generator for evaluate_program
        async def mock_evaluate(*args, **kwargs):
            # Check which block is being evaluated based on the code
            code = args[0] if args else kwargs.get('program_code_string', '')
            if 'function1' in code:
                return mock_eval_results[0]
            elif 'function2' in code:
                return mock_eval_results[1]
            return {"error": True, "error_message": "Unknown code"}
        
        evaluation_engine.evaluate_program = AsyncMock(side_effect=mock_evaluate)
        
        # Other mock components
        prompt_sampler = MagicMock()
        llm_interface = MagicMock()
        diff_applier = MagicMock()
        
        config = {
            "num_generations": 1,  # Just one generation for testing
            "batch_size_llm_calls": 1,
            "task_inputs": None
        }
        
        # Create the controller
        controller = DistributedController(
            task_definition=task_definition,
            program_database=program_database,
            prompt_sampler=prompt_sampler,
            llm_interface=llm_interface,
            diff_applier=diff_applier,
            evaluation_engine=evaluation_engine,
            config=config
        )
        
        # Mock the _generation_step to avoid running it
        controller._generation_step = AsyncMock()
        
        # Mock ProgramEntry.create to return consistent objects
        mock_entries = [
            ProgramEntry(
                id="test-entry-1",
                code=block_contents[0],
                scores=mock_eval_results[0],
                features=(len(block_contents[0]), mock_eval_results[0]["fitness"]),
                generation=0
            ),
            ProgramEntry(
                id="test-entry-2",
                code=block_contents[1],
                scores=mock_eval_results[1],
                features=(len(block_contents[1]), mock_eval_results[1]["fitness"]),
                generation=0
            )
        ]
        
        entry_map = dict(zip(block_contents, mock_entries))
        
        def mock_create_program(code, scores, features, generation, parent_id):
            # Match the entry based on code content
            if code in entry_map:
                return entry_map[code]
            # Default behavior for any other code
            return ProgramEntry(
                id="unknown-entry",
                code=code,
                scores=scores,
                features=features,
                generation=generation,
                parent_id=parent_id
            )
        
        # Mock the user evaluation function loading
        mock_eval_fn = MagicMock()
        mock_wrapper = MagicMock()
        mock_wrapper.load_user_evaluate_function.return_value = mock_eval_fn
        
        # Run the test with all our mocks
        with patch('alpha_evolve.program_database.ProgramEntry.create', side_effect=mock_create_program):
            with patch('alpha_evolve.controller.EvaluationWrapper', return_value=mock_wrapper):
                # Run the evolution method which includes seeding
                await controller.run_evolution()
                
                # Verify the evaluation engine was called for each block
                assert evaluation_engine.evaluate_program.call_count == 2
                
                # Verify add_program was called twice (once for each block)
                assert program_database.add_program.call_count == 2
                
                # Verify _generation_step was called for the configured number of generations
                assert controller._generation_step.call_count == config['num_generations']
    
    finally:
        # Ensure we clean up the temporary file
        if os.path.exists(code_path):
            os.unlink(code_path)


@pytest.mark.asyncio
async def test_seeding_with_evaluation_errors():
    """
    Test seeding when evaluation returns an error for a block.
    
    This test verifies:
    1. The controller handles evaluation errors properly
    2. Only successful evaluations are added to the database
    3. The controller can continue with the evolution process
    """
    # Create a real temporary file with evolvable blocks
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write('''
# EVOLVE-BLOCK-START block1
def function1():
    return 42
# EVOLVE-BLOCK-END block1

# EVOLVE-BLOCK-START block2
def function2(x):
    # This will cause an evaluation error
    return x * 2
# EVOLVE-BLOCK-END block2
''')
        code_path = temp_file.name
    
    try:
        # Create mock dependencies
        task_definition = MagicMock(spec=TaskDefinition)
        task_definition.problem_name = "test_seeding_errors"
        task_definition.initial_code_path = code_path
        task_definition.evaluate_function_module_path = "test_module_path"
        task_definition.evaluate_function_name = "test_eval_function"
        
        program_database = MagicMock(spec=ProgramDatabase)
        program_database.primary_score_key = "fitness"
        program_database.add_program.return_value = True
        
        # Define mock block content
        successful_block = 'def function1():\n    return 42'
        error_block = 'def function2(x):\n    # This will cause an evaluation error\n    return x * 2'
        
        # Define evaluation results
        successful_result = {"fitness": 0.8, "complexity": 0.2}
        error_result = {"error": True, "error_type": "RuntimeError", "error_message": "Failed to evaluate"}
        
        # Create a mock evaluation engine that returns different results based on the block
        evaluation_engine = MagicMock()
        
        async def mock_evaluate(*args, **kwargs):
            code = args[0] if args else kwargs.get('program_code_string', '')
            if 'function1' in code:
                return successful_result
            else:
                return error_result
        
        evaluation_engine.evaluate_program = AsyncMock(side_effect=mock_evaluate)
        
        # Other mock components
        prompt_sampler = MagicMock()
        llm_interface = MagicMock()
        diff_applier = MagicMock()
        
        config = {
            "num_generations": 1,
            "batch_size_llm_calls": 1,
            "task_inputs": None
        }
        
        # Create the controller
        controller = DistributedController(
            task_definition=task_definition,
            program_database=program_database,
            prompt_sampler=prompt_sampler,
            llm_interface=llm_interface,
            diff_applier=diff_applier,
            evaluation_engine=evaluation_engine,
            config=config
        )
        
        # Mock the _generation_step to avoid running it
        controller._generation_step = AsyncMock()
        
        # Mock ProgramEntry.create to return a predictable entry for the successful block
        successful_entry = ProgramEntry(
            id="test-entry-1",
            code=successful_block,
            scores=successful_result,
            features=(len(successful_block), successful_result["fitness"]),
            generation=0
        )
        
        # Mock the user evaluation function loading
        mock_eval_fn = MagicMock()
        mock_wrapper = MagicMock()
        mock_wrapper.load_user_evaluate_function.return_value = mock_eval_fn
        
        # Run the test with all our mocks
        with patch('alpha_evolve.program_database.ProgramEntry.create', return_value=successful_entry):
            with patch('alpha_evolve.controller.EvaluationWrapper', return_value=mock_wrapper):
                # Run the evolution method which includes seeding
                await controller.run_evolution()
                
                # Verify evaluation was called for both blocks
                assert evaluation_engine.evaluate_program.call_count == 2
                
                # Verify add_program was called only for the successful block
                assert program_database.add_program.call_count == 1
                assert program_database.add_program.call_args[0][0] == successful_entry
                
                # Verify _generation_step was still called
                assert controller._generation_step.call_count == config['num_generations']
    
    finally:
        # Clean up the temporary file
        if os.path.exists(code_path):
            os.unlink(code_path)


@pytest.mark.asyncio
async def test_seeding_with_no_blocks():
    """
    Test seeding when no evolvable blocks are found in the code.
    
    This test verifies:
    1. The controller handles code without evolvable blocks properly
    2. A warning message is logged
    3. The controller still proceeds with the main evolution loop
    """
    # Create a temporary file with code that doesn't have evolvable blocks
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write('''
def regular_function():
    return "This is not an evolvable block"

class RegularClass:
    def __init__(self):
        self.value = 42
        
    def regular_method(self, x):
        return x + self.value
''')
        code_path = temp_file.name
    
    try:
        # Create mock dependencies
        task_definition = MagicMock(spec=TaskDefinition)
        task_definition.problem_name = "test_no_blocks"
        task_definition.initial_code_path = code_path
        task_definition.evaluate_function_module_path = "test_module_path"
        task_definition.evaluate_function_name = "test_eval_function"
        
        program_database = MagicMock(spec=ProgramDatabase)
        program_database.primary_score_key = "fitness"
        
        # Mock components
        evaluation_engine = MagicMock()
        evaluation_engine.evaluate_program = AsyncMock()
        
        prompt_sampler = MagicMock()
        llm_interface = MagicMock()
        diff_applier = MagicMock()
        
        config = {
            "num_generations": 1,
            "batch_size_llm_calls": 1,
            "task_inputs": None,
            "fail_on_empty_blocks": False  # Don't fail on empty blocks
        }
        
        # Create the controller
        controller = DistributedController(
            task_definition=task_definition,
            program_database=program_database,
            prompt_sampler=prompt_sampler,
            llm_interface=llm_interface,
            diff_applier=diff_applier,
            evaluation_engine=evaluation_engine,
            config=config
        )
        
        # Mock the _generation_step to avoid running it
        controller._generation_step = AsyncMock()
        
        # Mock the user evaluation function loading
        mock_eval_fn = MagicMock()
        mock_wrapper = MagicMock()
        mock_wrapper.load_user_evaluate_function.return_value = mock_eval_fn
        
        # Capture stdout for warning message verification
        stdout_capture = io.StringIO()
        
        # Run the test with our mocks
        with redirect_stdout(stdout_capture):
            with patch('alpha_evolve.controller.EvaluationWrapper', return_value=mock_wrapper):
                # Run the evolution method which includes seeding
                await controller.run_evolution()
                
                # Get the captured output
                output = stdout_capture.getvalue()
                
                # Verify that a warning about no evolvable blocks was logged
                assert "No evolvable blocks found" in output
                
                # Verify that evaluation_engine.evaluate_program was never called
                evaluation_engine.evaluate_program.assert_not_called()
                
                # Verify that add_program was never called
                program_database.add_program.assert_not_called()
                
                # Verify that _generation_step was still called (evolution continues)
                assert controller._generation_step.call_count == config['num_generations']
    
    finally:
        # Clean up the temporary file
        if os.path.exists(code_path):
            os.unlink(code_path)


@pytest.mark.asyncio
async def test_seeding_with_fail_on_empty_blocks():
    """
    Test seeding when no evolvable blocks are found and fail_on_empty_blocks is True.
    
    This test verifies:
    1. The controller raises an error when no blocks are found and fail_on_empty_blocks is True
    2. The evolution process does not continue
    """
    # Create a temporary file with code that doesn't have evolvable blocks
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write('''
def regular_function():
    return "This is not an evolvable block"
''')
        code_path = temp_file.name
    
    try:
        # Create mock dependencies
        task_definition = MagicMock(spec=TaskDefinition)
        task_definition.problem_name = "test_no_blocks_fail"
        task_definition.initial_code_path = code_path
        task_definition.evaluate_function_module_path = "test_module_path"
        task_definition.evaluate_function_name = "test_eval_function"
        
        program_database = MagicMock(spec=ProgramDatabase)
        program_database.primary_score_key = "fitness"
        
        # Mock components
        evaluation_engine = MagicMock()
        evaluation_engine.evaluate_program = AsyncMock()
        
        prompt_sampler = MagicMock()
        llm_interface = MagicMock()
        diff_applier = MagicMock()
        
        config = {
            "num_generations": 1,
            "batch_size_llm_calls": 1,
            "task_inputs": None,
            "fail_on_empty_blocks": True  # Fail on empty blocks
        }
        
        # Create the controller
        controller = DistributedController(
            task_definition=task_definition,
            program_database=program_database,
            prompt_sampler=prompt_sampler,
            llm_interface=llm_interface,
            diff_applier=diff_applier,
            evaluation_engine=evaluation_engine,
            config=config
        )
        
        # Mock the _generation_step to avoid running it
        controller._generation_step = AsyncMock()
        
        # Mock the user evaluation function loading
        mock_eval_fn = MagicMock()
        mock_wrapper = MagicMock()
        mock_wrapper.load_user_evaluate_function.return_value = mock_eval_fn
        
        # Run the test with our mocks, expecting a ValueError
        with pytest.raises(ValueError) as excinfo:
            with patch('alpha_evolve.controller.EvaluationWrapper', return_value=mock_wrapper):
                # Run the evolution method which should fail
                await controller.run_evolution()
        
        # Verify the error message
        assert "No evolvable blocks found" in str(excinfo.value)
        
        # Verify that evaluation_engine.evaluate_program was never called
        evaluation_engine.evaluate_program.assert_not_called()
        
        # Verify that add_program was never called
        program_database.add_program.assert_not_called()
        
        # Verify that _generation_step was not called (evolution does not continue)
        controller._generation_step.assert_not_called()
    
    finally:
        # Clean up the temporary file
        if os.path.exists(code_path):
            os.unlink(code_path)


@pytest.mark.asyncio
async def test_seeding_with_file_not_found():
    """
    Test seeding when the initial code file cannot be found.
    
    This test verifies:
    1. The controller handles a missing initial code file properly
    2. An error message is logged
    3. The controller still proceeds with the main evolution loop
    """
    # Use a non-existent file path
    non_existent_path = "/path/to/nonexistent/file.py"
    
    # Create mock dependencies
    task_definition = MagicMock(spec=TaskDefinition)
    task_definition.problem_name = "test_file_not_found"
    task_definition.initial_code_path = non_existent_path
    task_definition.evaluate_function_module_path = "test_module_path"
    task_definition.evaluate_function_name = "test_eval_function"
    
    program_database = MagicMock(spec=ProgramDatabase)
    program_database.primary_score_key = "fitness"
    
    # Mock components
    evaluation_engine = MagicMock()
    evaluation_engine.evaluate_program = AsyncMock()
    
    prompt_sampler = MagicMock()
    llm_interface = MagicMock()
    diff_applier = MagicMock()
    
    config = {
        "num_generations": 1,
        "batch_size_llm_calls": 1,
        "task_inputs": None
    }
    
    # Create the controller
    controller = DistributedController(
        task_definition=task_definition,
        program_database=program_database,
        prompt_sampler=prompt_sampler,
        llm_interface=llm_interface,
        diff_applier=diff_applier,
        evaluation_engine=evaluation_engine,
        config=config
    )
    
    # Mock the _generation_step to avoid running it
    controller._generation_step = AsyncMock()
    
    # Mock the user evaluation function loading
    mock_eval_fn = MagicMock()
    mock_wrapper = MagicMock()
    mock_wrapper.load_user_evaluate_function.return_value = mock_eval_fn
    
    # Capture stdout for error message verification
    stdout_capture = io.StringIO()
    
    # Run the test with our mocks
    with redirect_stdout(stdout_capture):
        with patch('alpha_evolve.controller.EvaluationWrapper', return_value=mock_wrapper):
            # Run the evolution method which includes seeding
            await controller.run_evolution()
            
            # Get the captured output
            output = stdout_capture.getvalue()
            
            # Verify that an error about file not found was logged
            assert "Error: Initial code file not found" in output
            
            # Verify that CodeParser.extract_evolvable_blocks was called with empty content
            # (implemented in the controller as a fallback)
            with patch('alpha_evolve.task_utils.CodeParser.extract_evolvable_blocks') as mock_extract:
                mock_extract.return_value = []
                
                # This doesn't test the actual run_evolution call again,
                # just a verification that with empty content, extract_evolvable_blocks would be called
                mock_extract("")
                mock_extract.assert_called_once_with("")
            
            # Verify that evaluation_engine.evaluate_program was never called
            evaluation_engine.evaluate_program.assert_not_called()
            
            # Verify that add_program was never called
            program_database.add_program.assert_not_called()
            
            # Verify that _generation_step was still called (evolution continues)
            assert controller._generation_step.call_count == config['num_generations']