# Installation

This guide will walk you through installing AlphaEvolve and setting up your development environment.

## System Requirements

Before installing AlphaEvolve, ensure your system meets the following requirements:

### Python Version
- **Python 3.12 or higher** is required
- Check your Python version: `python --version`

### System Resources
- **Memory**: 4GB RAM minimum, 8GB recommended for large experiments
- **Storage**: At least 1GB free space for evolution data and checkpoints
- **CPU**: Multi-core processor recommended for parallel evaluation

### Optional Dependencies
- **Docker**: For enhanced sandboxing security (recommended for production)
- **Git**: For version control and accessing example repositories

## Installation Methods

### Using pip (Recommended)

The easiest way to install AlphaEvolve is using pip:

```bash
pip install alphaevolve
```

For development work, install with development dependencies:

```bash
pip install "alphaevolve[dev]"
```

### Using uv (Faster Alternative)

If you prefer the faster uv package manager:

```bash
uv add alphaevolve
```

### From Source

For the latest development version or to contribute:

```bash
# Clone the repository
git clone https://github.com/alphaevolve/alphaevolve.git
cd alphaevolve

# Install in development mode
pip install -e ".[dev]"
```

## Verify Installation

After installation, verify that AlphaEvolve is working correctly:

```bash
# Check version
alphaevolve --version

# Run system status check
alphaevolve status
```

You should see output similar to:

```
AlphaEvolve System Status

Configuration
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Setting      ┃ Value               ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ Project Name │ AlphaEvolve Project │
│ Version      │ 1.0.0               │
│ Environment  │ development         │
│ Debug Mode   │ False               │
└──────────────┴─────────────────────┘

Configuration is valid
```

## Setting Up LLM Access

To use real language models (OpenAI, Anthropic), you'll need API keys:

### OpenAI Setup

1. Create an account at [OpenAI](https://platform.openai.com/)
2. Generate an API key from your dashboard
3. Set the environment variable:

```bash
export OPENAI_API_KEY="your-openai-api-key-here"
```

### Anthropic Setup

1. Create an account at [Anthropic](https://console.anthropic.com/)
2. Generate an API key from your console
3. Set the environment variable:

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
```

### Environment File (Optional)

Create a `.env` file in your project directory:

```bash
# .env
OPENAI_API_KEY=your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

## Docker Setup (Optional)

For enhanced security and isolation, install Docker:

### Ubuntu/Debian
```bash
sudo apt update
sudo apt install docker.io
sudo systemctl start docker
sudo systemctl enable docker
```

### macOS
```bash
brew install --cask docker
```

### Windows
Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/).

After installation, verify Docker is working:

```bash
docker --version
alphaevolve status  # Should show Docker sandbox available
```

## Initial Configuration

Set up your first AlphaEvolve project:

```bash
# Create project directory
mkdir my-evolution-project
cd my-evolution-project

# Initialize configuration
alphaevolve setup --template basic

# For research use with real LLMs
alphaevolve setup --template research
```

This creates an `alphaevolve.yaml` configuration file you can customize.

## Troubleshooting

### Common Issues

**Python Version Error**
```
ERROR: Python 3.12 or higher is required
```
Solution: Upgrade Python or use a virtual environment with the correct version.

**Permission Error**
```
ERROR: Permission denied
```
Solution: Use `--user` flag with pip or create a virtual environment.

**Docker Not Found**
```
WARNING: Docker not available, using process sandbox
```
Solution: Install Docker or continue with process-based sandboxing.

### Virtual Environment Setup

If you encounter dependency conflicts, use a virtual environment:

```bash
# Create virtual environment
python -m venv alphaevolve-env

# Activate (Linux/macOS)
source alphaevolve-env/bin/activate

# Activate (Windows)
alphaevolve-env\Scripts\activate

# Install AlphaEvolve
pip install alphaevolve
```

### Getting Help

If you encounter issues:

1. Check the [troubleshooting guide](../user-guide/troubleshooting.md)
2. Search [existing issues](https://github.com/alphaevolve/alphaevolve/issues)
3. Ask for help in [discussions](https://github.com/alphaevolve/alphaevolve/discussions)
4. Create a new issue with system details

## Next Steps

With AlphaEvolve installed, you're ready to:

- Follow the [Quick Start Guide](quickstart.md) for your first evolution experiment
- Learn about [Configuration](configuration.md) options
- Explore [Examples](../examples/algorithm-optimization.md) for your use case

## Development Installation

For contributors and advanced users who want to modify AlphaEvolve:

```bash
# Clone with development setup
git clone https://github.com/alphaevolve/alphaevolve.git
cd alphaevolve

# Install development dependencies
pip install -e ".[dev]"

# Run tests to verify setup
pytest

# Install pre-commit hooks
pre-commit install
```

See the [Contributing Guide](../developer-guide/contributing.md) for detailed development setup instructions.