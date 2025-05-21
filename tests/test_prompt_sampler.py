"""
Tests for the PromptSampler class.
"""

import pytest
from unittest.mock import MagicMock
from typing import Dict, Tuple, Optional

from alpha_evolve.program_database import ProgramDatabase, ProgramEntry
from alpha_evolve.prompt_sampler import PromptSampler


@pytest.fixture
def mock_program_database():
    """
    Create a mock ProgramDatabase with predefined program entries.
    """
    db = MagicMock(spec=ProgramDatabase)
    
    # Create some mock program entries
    parent_program = MagicMock(spec=ProgramEntry)
    parent_program.id = "parent1"
    parent_program.code = "def example_func():\n    return 42"
    parent_program.scores = {"accuracy": 0.8, "efficiency": 0.7}
    parent_program.features = (0.8, 0.7)
    parent_program.generation = 1
    
    inspiration_program = MagicMock(spec=ProgramEntry)
    inspiration_program.id = "inspiration1"
    inspiration_program.code = "def example_func():\n    result = 42\n    return result"
    inspiration_program.scores = {"accuracy": 0.9, "efficiency": 0.8}
    inspiration_program.features = (0.9, 0.8)
    inspiration_program.generation = 2
    
    # Configure the mock database to return the mock entries
    def get_program_by_id(program_id):
        if program_id == "parent1":
            return parent_program
        elif program_id == "inspiration1":
            return inspiration_program
        else:
            return None
    
    db.get_program_by_id.side_effect = get_program_by_id
    
    return db


def test_prompt_sampler_initialization(mock_program_database):
    """
    Test that PromptSampler initializes correctly with a program database.
    """
    sampler = PromptSampler(mock_program_database)
    assert sampler.program_database == mock_program_database


def test_format_program_for_prompt(mock_program_database):
    """
    Test the _format_program_for_prompt helper method.
    """
    sampler = PromptSampler(mock_program_database)
    parent_program = mock_program_database.get_program_by_id("parent1")
    
    formatted = sampler._format_program_for_prompt(parent_program, "Test Role")
    
    # Check that the formatted string contains the program details
    assert "### Test Role (ID: parent1)" in formatted
    assert "#### Scores" in formatted
    assert "- accuracy: 0.8" in formatted
    assert "- efficiency: 0.7" in formatted
    assert "#### Code" in formatted
    assert "```python" in formatted
    assert "def example_func():" in formatted
    assert "return 42" in formatted


def test_create_evolution_prompt_with_valid_ids(mock_program_database):
    """
    Test create_evolution_prompt with valid parent and inspiration program IDs.
    """
    sampler = PromptSampler(mock_program_database)
    
    prompt = sampler.create_evolution_prompt(
        parent_program_ids=["parent1"],
        inspiration_program_ids=["inspiration1"]
    )
    
    # Check that the prompt contains system instructions
    assert "You are an expert coding assistant" in prompt
    
    # Check that it contains diff format instructions
    assert "Provide your changes in a diff format" in prompt
    assert "<<<<<<<< SEARCH" in prompt
    assert "========" in prompt
    assert ">>>>>>>> REPLACE" in prompt
    
    # Check that it contains parent program information
    assert "## Parent Programs to Evolve" in prompt
    assert "### Parent Program 1 (ID: parent1)" in prompt
    assert "- accuracy: 0.8" in prompt
    assert "def example_func():" in prompt
    assert "return 42" in prompt
    
    # Check that it contains inspiration program information
    assert "## Inspiration Programs" in prompt
    assert "### Inspiration Program 1 (ID: inspiration1)" in prompt
    assert "- efficiency: 0.8" in prompt
    assert "result = 42" in prompt


def test_create_evolution_prompt_with_full_code_format(mock_program_database):
    """
    Test create_evolution_prompt with full_code output format.
    """
    sampler = PromptSampler(mock_program_database)
    
    prompt = sampler.create_evolution_prompt(
        parent_program_ids=["parent1"],
        inspiration_program_ids=["inspiration1"],
        desired_output_format="full_code"
    )
    
    # Check that it contains the full code instructions instead of diff format
    assert "Provide the complete evolved code block." in prompt
    assert "<<<<<<<< SEARCH" not in prompt
    
    # Check that other aspects of the prompt are still present
    assert "You are an expert coding assistant" in prompt
    assert "### Parent Program 1 (ID: parent1)" in prompt
    assert "### Inspiration Program 1 (ID: inspiration1)" in prompt


def test_create_evolution_prompt_with_task_context(mock_program_database):
    """
    Test create_evolution_prompt with a task context.
    """
    sampler = PromptSampler(mock_program_database)
    
    task_context = "Optimize the function for better time complexity."
    prompt = sampler.create_evolution_prompt(
        parent_program_ids=["parent1"],
        inspiration_program_ids=["inspiration1"],
        task_context=task_context
    )
    
    # Check that the task context is included in the prompt
    assert "### Task Context" in prompt
    assert task_context in prompt


def test_create_evolution_prompt_with_invalid_parent_id(mock_program_database):
    """
    Test create_evolution_prompt with an invalid parent program ID.
    """
    sampler = PromptSampler(mock_program_database)
    
    with pytest.raises(ValueError) as excinfo:
        sampler.create_evolution_prompt(
            parent_program_ids=["nonexistent_id"],
            inspiration_program_ids=["inspiration1"]
        )
    
    assert "Parent program with ID nonexistent_id not found" in str(excinfo.value)


def test_create_evolution_prompt_with_invalid_inspiration_id(mock_program_database):
    """
    Test create_evolution_prompt with an invalid inspiration program ID.
    """
    sampler = PromptSampler(mock_program_database)
    
    with pytest.raises(ValueError) as excinfo:
        sampler.create_evolution_prompt(
            parent_program_ids=["parent1"],
            inspiration_program_ids=["nonexistent_id"]
        )
    
    assert "Inspiration program with ID nonexistent_id not found" in str(excinfo.value)


def test_create_evolution_prompt_with_multiple_programs(mock_program_database):
    """
    Test create_evolution_prompt with multiple parent and inspiration programs.
    """
    # Create additional mock program
    another_parent = MagicMock(spec=ProgramEntry)
    another_parent.id = "parent2"
    another_parent.code = "def another_func():\n    return 100"
    another_parent.scores = {"accuracy": 0.75, "efficiency": 0.65}
    another_parent.features = (0.75, 0.65)
    another_parent.generation = 1
    
    # Create a dictionary to return programs based on IDs
    program_dict = {
        "parent1": mock_program_database.get_program_by_id("parent1"),
        "parent2": another_parent,
        "inspiration1": mock_program_database.get_program_by_id("inspiration1")
    }
    
    # Create a new side_effect function
    def updated_get_program_by_id(program_id):
        return program_dict.get(program_id)
    
    # Update the mock_program_database
    mock_program_database.get_program_by_id.side_effect = updated_get_program_by_id
    
    sampler = PromptSampler(mock_program_database)
    
    prompt = sampler.create_evolution_prompt(
        parent_program_ids=["parent1", "parent2"],
        inspiration_program_ids=["inspiration1"]
    )
    
    # Check that both parent programs are included
    assert "### Parent Program 1 (ID: parent1)" in prompt
    assert "### Parent Program 2 (ID: parent2)" in prompt
    assert "def another_func():" in prompt
    assert "return 100" in prompt