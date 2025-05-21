# AlphaEvolve

AlphaEvolve is a Python-based system that combines evolutionary algorithms with Large Language Models (LLMs) to optimize and evolve code. It uses a MAP-Elites evolutionary algorithm to maintain a diverse population of code variants while optimizing for performance and other features.

## =Ë Overview

AlphaEvolve identifies code blocks marked for evolution in your program, generates modifications using LLMs, evaluates their performance, and iteratively improves the code through a structured evolutionary process. The system maintains diversity by using a MAP-Elites archive that organizes program variants based on different feature dimensions.

### Key Features

- >ì **Evolutionary Code Optimization** - Automatically evolves and optimizes code blocks
- > **LLM Integration** - Uses Large Language Models to generate code modifications
- =Ê **MAP-Elites Archive** - Maintains diversity in the solution population
- = **Distributed Evolution** - Supports multiple evolutionary islands (planned)
- =Ý **Diff-Based Modifications** - Uses diffs to apply precise, targeted code changes

## =' Installation

AlphaEvolve requires Python 3.12 or newer.

```bash
# Clone the repository
git clone https://github.com/your-username/alphaevolve.git
cd alphaevolve

# Install in development mode
python -m pip install -e ".[dev]"
```

## =€ Usage

### Basic Usage

1. Create a Python file with code blocks marked for evolution:

```python
# EVOLVE-BLOCK-START my_block_name
def my_function(x, y):
    # This code will be evolved by AlphaEvolve
    result = x * 2 + y
    return result
# EVOLVE-BLOCK-END my_block_name
```

2. Create an evaluator function (see `evaluator.py` for an example) to assess code performance.

3. Run the evolution process:

```bash
python -m alpha_evolve.main
```

### Configuration

The main configuration is defined in `alpha_evolve/main.py`. Key parameters include:

- `num_generations`: Number of evolutionary generations to run
- `batch_size_new_programs`: Number of new programs to generate in each generation
- `primary_score_key`: Key for the primary objective score (default: "objective")
- `llm_type`: Type of LLM to use ("pro" or "flash")
- `feature_dimensions_bins`: Bins for the MAP-Elites archive dimensions

## =Ú Core Components

1. **Task Definition & Code Parsing** (`task_utils.py`) 
   - Defines task specifications
   - Parses code blocks marked for evolution

2. **Program Database** (`program_database.py`)
   - Implements MAP-Elites archive for maintaining diverse solutions
   - Tracks all program variants through evolution

3. **LLM Interface** (`llm_interface.py`)
   - Interfaces with LLMs to generate code modifications
   - Currently uses mock LLMs, with real LLM integration planned

4. **Diff Applier** (`diff_applier.py`)
   - Applies LLM-generated diffs to code blocks
   - Handles code replacement and modification

5. **Evaluation Engine** (`evaluation_engine.py`)
   - Evaluates modified code using user-provided functions
   - Provides scores for the evolutionary process

6. **Distributed Controller** (`controller.py`)
   - Orchestrates the evolutionary process
   - Manages communication between components

## >ê Testing

Run the test suite with pytest:

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_task_utils.py

# Run tests with verbose output
pytest -xvs tests/
```

## =È Future Development

See the [TODO.md](TODO.md) file for planned enhancements, including:

- Complete island model migration for distributed evolution
- Enhanced MAP-Elites archive with visualization
- Integration with real LLM APIs
- Advanced security and sandboxing for code execution
- Performance optimizations and parallel evaluation

## =Ä License

[Insert License Information Here]

## =Ú References

- AlphaEvolve paper (see `paper/AlphaEvolve.pdf`)