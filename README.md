# AlphaEvolve

AlphaEvolve is a Python-based system that combines evolutionary algorithms with Large Language Models (LLMs) to optimize and evolve code. It uses a MAP-Elites evolutionary algorithm to maintain a diverse population of code variants while optimizing for performance and other features.

## =� Overview

AlphaEvolve identifies code blocks marked for evolution in your program, generates modifications using LLMs, evaluates their performance, and iteratively improves the code through a structured evolutionary process. The system maintains diversity by using a MAP-Elites archive that organizes program variants based on different feature dimensions.

### Key Features

- >� **Evolutionary Code Optimization** - Automatically evolves and optimizes code blocks
- > **LLM Integration** - Uses Large Language Models to generate code modifications
- =� **MAP-Elites Archive** - Maintains diversity in the solution population
- = **Distributed Evolution** - Supports multiple evolutionary islands (planned)
- =� **Diff-Based Modifications** - Uses diffs to apply precise, targeted code changes

## =' Installation

AlphaEvolve requires Python 3.12 or newer.

```bash
# Clone the repository
git clone https://github.com/your-username/alphaevolve.git
cd alphaevolve

# Install in development mode
python -m pip install -e ".[dev]"
```

## =� Usage

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

AlphaEvolve uses a comprehensive configuration system with YAML/JSON files and environment variables:

1. **Create configuration file:**
```bash
cp config/alphaevolve.example.yaml alphaevolve.yaml
```

2. **Set LLM API keys:**
```bash
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
```

3. **Key configuration sections:**
- `llm`: LLM provider settings (default_provider, API keys, rate limits)
- `sandbox`: Code execution security (Docker/process isolation, resource limits)
- `evolution`: Evolutionary parameters (generations, population size, mutation rates)
- `database`: MAP-Elites archive settings (feature dimensions, bins)

See `config/alphaevolve.example.yaml` for all available options.

## =� Core Components

1. **Task Definition & Code Parsing** (`task_utils.py`) 
   - Defines task specifications
   - Parses code blocks marked for evolution

2. **Program Database** (`program_database.py`)
   - Implements MAP-Elites archive for maintaining diverse solutions
   - Tracks all program variants through evolution

3. **LLM Interface** (`llm_interface.py`)
   - Interfaces with LLMs to generate code modifications
   - Supports OpenAI, Anthropic, and mock providers with rate limiting

4. **Diff Applier** (`diff_applier.py`)
   - Applies LLM-generated diffs to code blocks
   - Handles code replacement and modification

5. **Evaluation Engine** (`evaluation_engine.py`)
   - Evaluates modified code using user-provided functions
   - Supports secure sandboxing with Docker and process isolation
   - Provides scores for the evolutionary process

6. **Distributed Controller** (`controller.py`)
   - Orchestrates the evolutionary process
   - Manages communication between components

## >� Testing

Run the test suite with pytest:

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_task_utils.py

# Run tests with verbose output
pytest -xvs tests/
```

## =� Future Development

See the [TODO.md](TODO.md) file for planned enhancements, including:

- Complete island model migration for distributed evolution
- Enhanced MAP-Elites archive with visualization
- ✅ ~~Integration with real LLM APIs~~ (Completed: OpenAI, Anthropic support)
- ✅ ~~Advanced security and sandboxing for code execution~~ (Completed: Docker/process sandboxing)
- ✅ ~~Configuration management system~~ (Completed: YAML/JSON with validation)
- Performance optimizations and parallel evaluation

## =� License

[Insert License Information Here]

## =� References

- AlphaEvolve paper (see `paper/AlphaEvolve.pdf`)