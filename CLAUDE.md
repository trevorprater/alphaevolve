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
   - Sends prompts to code-generating LLMs (OpenAI, Anthropic, Mock)
   - Processes the returned code modifications
   - Supports multiple providers with rate limiting and error handling

5. **Diff Applier** (`alpha_evolve/diff_applier.py`)
   - Applies LLM-generated diffs to code
   - Handles replacement of code blocks

6. **Evaluation Engine** (`alpha_evolve/evaluation.py`)
   - Evaluates modified code using user-provided functions
   - Supports secure sandboxing with Docker and process isolation

7. **Distributed Controller** (`alpha_evolve/controller.py`)
   - Orchestrates the evolutionary process
   - Manages the main evolution loop

8. **Configuration Management** (`alpha_evolve/config.py`)
   - Pydantic-based configuration system with validation
   - YAML/JSON file support with environment variable overlays
   - Secure credential management for LLM providers

9. **Persistent Storage** (`alpha_evolve/persistence.py`)
   - Program database serialization with compression and checksums
   - Evolution checkpointing for resumable experiments
   - Automatic backup and recovery mechanisms

## Development Environment

### Dependencies
- Python 3.12+
- pytest 8.3.5+
- pydantic-settings 2.11+ (for configuration management)
- aiohttp 3.8+ (for async LLM API calls)

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

# Configuration
cp config/alphaevolve.example.yaml alphaevolve.yaml  # Create config from example
export OPENAI_API_KEY="your-key"   # Set LLM API keys
export ANTHROPIC_API_KEY="your-key"

# Checkpoint management
alphaevolve checkpoint list         # List available checkpoints
alphaevolve checkpoint resume --checkpoint path  # Resume evolution
alphaevolve checkpoint clean --keep 5            # Cleanup old checkpoints
```

## Code Conventions

- Use dataclasses or Pydantic models for structured data
- Include type hints and docstrings for all functions and methods
- Follow PEP 8 style guidelines
- Implement proper error handling with custom exceptions when needed
- Use async/await for potentially long-running operations (especially LLM interactions)

## Workflow Memories

- git commit every atomic completed taskmaster task