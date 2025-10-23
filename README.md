# AlphaEvolve

A weekend ripoff of Google's paper.

*<begin Claude 3.7 emoji-garble>*


AlphaEvolve is a Python-based system that combines evolutionary algorithms with Large Language Models (LLMs) to optimize and evolve code. It uses a MAP-Elites evolutionary algorithm to maintain a diverse population of code variants while optimizing for performance and other features.

## 🔬 Overview

AlphaEvolve identifies code blocks marked for evolution in your program, generates modifications using LLMs, evaluates their performance, and iteratively improves the code through a structured evolutionary process. The system maintains diversity by using a MAP-Elites archive that organizes program variants based on different feature dimensions.

### Key Features

- 🧬 **Evolutionary Code Optimization** - Automatically evolves and optimizes code blocks
- 🤖 **Modern LLM Integration** - Supports latest models from OpenAI, Anthropic, and Google
- 📊 **MAP-Elites Archive** - Maintains diversity in the solution population
- 🔒 **Secure Sandboxing** - Safe code execution with Docker/process isolation
- 💾 **Persistent Storage** - Checkpoint and resume evolution experiments
- 🎯 **Diff-Based Modifications** - Uses diffs to apply precise, targeted code changes
- ⚡ **Production-Grade Evaluation** - Advanced evaluation engine with cascades, approximation, and parallel processing

## 📦 Installation

AlphaEvolve requires Python 3.12 or newer.

```bash
# Clone the repository
git clone https://github.com/your-username/alphaevolve.git
cd alphaevolve

# Install using uv (recommended)
uv pip install -e ".[dev]"

# Or using pip
python -m pip install -e ".[dev]"

# Optional: Install LLM SDK packages
uv pip install openai anthropic google-genai
```

## 🚀 Usage

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
# Using the CLI (recommended)
alphaevolve evolve --source your_file.py --generations 10 --interactive

# Or using the Python module directly
python -m alpha_evolve.main
```

### CLI Usage

AlphaEvolve provides a comprehensive command-line interface:

```bash
# Initialize project configuration
alphaevolve setup --template research

# Run evolution with interactive monitoring
alphaevolve evolve --source code.py --generations 10 --interactive

# Analyze evolution results
alphaevolve analyze --database results.json --format table

# Check system status
alphaevolve status

# Manage evolution checkpoints
alphaevolve checkpoint list
alphaevolve checkpoint resume --checkpoint path/to/checkpoint
alphaevolve checkpoint clean --keep 5
```

### Configuration

AlphaEvolve uses a comprehensive configuration system with YAML/JSON files and environment variables:

1. **Initialize configuration:**
```bash
alphaevolve setup --template basic|research|production
```

2. **Set LLM API keys:**
```bash
# For OpenAI (o4, o3, o1 models)
export OPENAI_API_KEY="your-openai-key"

# For Anthropic (Claude models with thinking)
export ANTHROPIC_API_KEY="your-anthropic-key"

# For Google Gemini
export GOOGLE_API_KEY="your-google-api-key"

# For Vertex AI (Google Cloud)
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

3. **Key configuration sections:**
- `llm`: LLM provider settings (default_provider, API keys, rate limits)
  - Supports OpenAI (o4, o3, o1), Anthropic (Claude 4 with thinking), Google Gemini/Vertex AI
- `sandbox`: Code execution security (Docker/process isolation, resource limits)
- `evaluation`: Advanced evaluation settings (cascades, approximation, parallel processing)
- `evolution`: Evolutionary parameters (generations, population size, mutation rates)
- `database`: MAP-Elites archive settings (feature dimensions, bins)
- `persistence`: Checkpoint intervals and auto-save settings

See `config/alphaevolve.example.yaml` for all available options.

## 🧩 Supported LLM Providers

AlphaEvolve supports the latest LLM models for code generation:

### OpenAI
- **o4** / **o4-mini**: Most advanced reasoning models
- **o3**: High-performance reasoning model
- **o1** / **o1-mini**: Production reasoning models
- **gpt-4** / **gpt-4o**: Standard GPT-4 models

### Anthropic
- **claude-opus-4**: Most capable model with thinking support
- **claude-sonnet-4**: Balanced model with thinking support
- **claude-3-5-sonnet-v2**: Fast, efficient model

### Google
- **gemini-2.5-flash**: Fast, efficient model
- **gemini-2.5-pro**: Advanced capabilities
- **Vertex AI**: Same models via Google Cloud

## 🏗️ Core Components

1. **Task Definition & Code Parsing** (`task_utils.py`) 
   - Defines task specifications
   - Parses code blocks marked for evolution

2. **Program Database** (`program_database.py`)
   - Implements MAP-Elites archive for maintaining diverse solutions
   - Tracks all program variants through evolution

3. **LLM Interface** (`llm_interface.py`)
   - Modern SDK integration with OpenAI, Anthropic, and Google
   - Automatic fallback, rate limiting, and cost tracking
   - Returns structured responses with metadata

4. **Diff Applier** (`diff_applier.py`)
   - Applies LLM-generated diffs to code blocks
   - Handles code replacement and modification

5. **Evaluation Engine** (`evaluation_engine.py`)
   - Evaluates modified code using user-provided functions
   - Supports secure sandboxing with Docker and process isolation
   - Advanced features: evaluation cascades, fitness approximation, parallel evaluation
   - Provides scores for the evolutionary process

6. **Distributed Controller** (`controller.py`)
   - Orchestrates the evolutionary process
   - Manages communication between components

7. **Advanced Feature Extraction** (`feature_extraction.py`)
   - AST-based code analysis with McCabe complexity and structure metrics
   - Textual analysis for code quality, naming conventions, and patterns
   - 12+ sophisticated features for comprehensive code characterization

8. **Configurable Feature System** (`feature_configuration.py`)
   - User-configurable feature functions with flexible API
   - Multiple binning strategies (uniform, adaptive, custom, percentile)
   - Runtime feature management with weights and validation

9. **Advanced MAP-Elites Archives** (`advanced_map_elites.py`)
   - CVT-MAP-Elites with Voronoi tessellation and adaptive centroids
   - Adaptive archives with dynamic bin splitting
   - Hierarchical archives with multi-resolution exploration
   - Production-grade diversity-aware program selection

10. **Sophisticated Diversity Metrics** (`diversity_metrics.py`)
    - 4 distinct diversity metrics: Semantic, Behavioral, Structural, Textual
    - CompositeDiversityMetric with configurable weights and detailed scoring
    - Performance-optimized implementations for large archive analysis

## 🧪 Testing

AlphaEvolve includes a comprehensive test suite with 371 tests covering all components:

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_task_utils.py

# Run tests with verbose output
pytest -xvs tests/

# Test with LLM SDKs installed
uv pip install openai anthropic google-genai
pytest -xvs tests/test_llm_interface.py tests/test_sdk_integration.py

# Test advanced evaluation engine features
pytest -xvs tests/test_evaluation_engine_advanced.py

# Test advanced MAP-Elites implementations
pytest -xvs tests/test_advanced_map_elites.py

# Test sophisticated feature extraction
pytest -xvs tests/test_feature_extraction.py tests/test_feature_configuration.py
```

## 📚 Documentation

Full documentation is available at `docs/` and can be viewed with:

```bash
mkdocs serve
```

Key documentation:
- [Getting Started Guide](docs/getting-started/quickstart.md)
- [LLM Provider Setup](docs/getting-started/llm-setup.md)
- [Configuration Reference](docs/user-guide/configuration-reference.md)
- [API Reference](docs/api-reference/)

## 🔮 Future Development

See the [TODO.md](TODO.md) file for planned enhancements, including:

- Complete island model migration for distributed evolution
- Enhanced MAP-Elites archive with visualization
- ✅ ~~Integration with real LLM APIs~~ (Completed: OpenAI, Anthropic, Google support)
- ✅ ~~Advanced security and sandboxing for code execution~~ (Completed: Docker/process sandboxing)
- ✅ ~~Configuration management system~~ (Completed: YAML/JSON with validation)
- ✅ ~~CLI interface for user interaction~~ (Completed: Rich CLI with interactive monitoring)
- ✅ ~~Persistent storage and checkpointing~~ (Completed: Auto-save, resume, backup system)
- ✅ ~~Production-grade evaluation engine~~ (Completed: Cascades, approximation, parallel evaluation)
- ✅ ~~Advanced MAP-Elites with sophisticated features~~ (Completed: CVT, adaptive, hierarchical archives with AST-based feature extraction)
- Enhanced distributed evolution with island model implementation

## 📄 License

[Insert License Information Here]

## 📖 References

- AlphaEvolve paper (see `paper/AlphaEvolve.pdf`)