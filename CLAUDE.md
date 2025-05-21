# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AlphaEvolve is a Python-based system that uses evolutionary techniques combined with Large Language Models (LLMs) to evolve and optimize code. The system identifies evolvable code blocks in a user's program, applies LLM-generated modifications, evaluates the results, and iteratively improves the code through a MAP-Elites evolutionary algorithm.

## Key Components

1. **TaskDefinition & Parsing Utils** (`alpha_evolve/task_utils.py`)
   - Defines task specifications
   - Parses evolvable code blocks marked with special comments
   - Loads and executes user-provided evaluation functions

2. **Program Database** (`alpha_evolve/program_database.py`)
   - Contains the `ProgramEntry` class for tracking code variations
   - Implements `MAPElitesArchive` for storing and selecting program variations

3. **Prompt Sampler** (`alpha_evolve/prompt_sampler.py`)
   - Samples programs from the database to create LLM prompts

4. **LLM Interface** (`alpha_evolve/llm_interface.py`)
   - Sends prompts to code-generating LLMs
   - Processes the returned code modifications

5. **Diff Applier** (`alpha_evolve/diff_applier.py`)
   - Applies LLM-generated diffs to code
   - Handles replacement of code blocks

6. **Evaluation Engine** (`alpha_evolve/evaluation.py`)
   - Evaluates modified code using user-provided functions

7. **Distributed Controller** (`alpha_evolve/controller.py`)
   - Orchestrates the evolutionary process
   - Manages the main evolution loop

## Development Environment

### Dependencies
- Python 3.12+
- pytest 8.3.5+

### Common Commands

```bash
# Install development dependencies 
python -m pip install -e ".[dev]"  # Install in development mode

# Running tests
pytest                             # Run all tests
pytest tests/test_task_utils.py    # Run a specific test file
pytest -xvs tests/                 # Run tests with verbose output

# Running the main application
python -m alpha_evolve.main        # Run the main evolution process
```

## Code Conventions

- Use dataclasses or Pydantic models for structured data
- Include type hints and docstrings for all functions and methods
- Follow PEP 8 style guidelines
- Implement proper error handling with custom exceptions when needed
- Use async/await for potentially long-running operations (especially LLM interactions)