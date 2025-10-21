# Contributing to AlphaEvolve

Thank you for your interest in contributing to AlphaEvolve! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow. Be respectful, inclusive, and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/your-username/alphaevolve.git
   cd alphaevolve
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/original-org/alphaevolve.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or newer
- [uv](https://github.com/astral-sh/uv) package manager (recommended)
- Docker (for sandbox testing)
- Git

### Installation

1. **Create a virtual environment** (optional but recommended):
   ```bash
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install development dependencies**:
   ```bash
   uv pip install -e ".[dev,llm]"
   ```

3. **Set up pre-commit hooks** (if available):
   ```bash
   pre-commit install
   ```

4. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

### Verify Installation

```bash
# Run tests
pytest

# Check code style
ruff check alpha_evolve/ tests/

# Build documentation
mkdocs serve
```

## How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check existing issues to avoid duplicates
- Collect relevant information (OS, Python version, error messages)

When creating a bug report, include:
- Clear, descriptive title
- Steps to reproduce the issue
- Expected vs. actual behavior
- Code samples or error messages
- Environment details (Python version, OS, dependencies)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. Include:
- Clear, descriptive title
- Detailed description of the proposed enhancement
- Use cases and benefits
- Any potential drawbacks or alternatives considered

### Contributing Code

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes** following our [coding standards](#coding-standards)

3. **Add tests** for your changes

4. **Update documentation** as needed

5. **Commit your changes** with clear commit messages:
   ```bash
   git commit -m "feat: add new feature"
   # or
   git commit -m "fix: resolve issue with..."
   ```

6. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** on GitHub

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:
- Line length: 100 characters (soft limit), 120 characters (hard limit)
- Use type hints for all function signatures
- Use docstrings (Google style) for all public functions and classes

### Code Formatting

We use `ruff` for linting and formatting:

```bash
# Check code style
ruff check alpha_evolve/ tests/

# Auto-format code
ruff format alpha_evolve/ tests/
```

### Type Checking

Use type hints throughout the codebase:

```python
from typing import List, Dict, Optional

def process_data(items: List[str], config: Dict[str, any]) -> Optional[str]:
    """Process data items according to configuration.

    Args:
        items: List of items to process
        config: Configuration dictionary

    Returns:
        Processed result or None if processing fails
    """
    pass
```

### Documentation Style

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of function.

    Longer description if needed, explaining the function's behavior,
    edge cases, and important details.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
        RuntimeError: When processing fails

    Examples:
        >>> function_name("test", 42)
        True
    """
    pass
```

### Error Handling

- Use specific exception types
- Include helpful error messages
- Log errors appropriately
- Clean up resources in `finally` blocks or context managers

```python
import logging

logger = logging.getLogger(__name__)

def risky_operation():
    try:
        # Operation that might fail
        result = perform_operation()
    except SpecificError as e:
        logger.error(f"Operation failed: {e}")
        raise RuntimeError(f"Failed to perform operation: {e}") from e
    finally:
        # Cleanup
        cleanup_resources()
```

### Async Code

- Use `async`/`await` for I/O-bound operations
- Use proper async context managers
- Handle exceptions in async code appropriately

```python
async def async_operation():
    async with resource_manager() as resource:
        result = await resource.perform_operation()
        return result
```

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_module.py

# Run with coverage
pytest --cov=alpha_evolve --cov-report=html

# Run with verbose output
pytest -vv

# Run only fast tests (skip slow integration tests)
pytest -m "not slow"
```

### Writing Tests

- Write tests for all new functionality
- Maintain or improve test coverage
- Use descriptive test names
- Test edge cases and error conditions
- Use fixtures for common setup
- Mock external dependencies (LLM APIs, Docker, etc.)

```python
import pytest
from alpha_evolve.module import function_to_test

def test_function_basic_case():
    """Test basic functionality of function."""
    result = function_to_test("input")
    assert result == "expected_output"

def test_function_edge_case():
    """Test function with edge case input."""
    with pytest.raises(ValueError):
        function_to_test("")

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await async_function_to_test()
    assert result is not None
```

## Documentation

### User Documentation

- Update docs in `docs/` directory when adding features
- Use clear, concise language
- Include code examples
- Keep documentation synchronized with code

### API Documentation

- Document all public APIs with docstrings
- Include examples in docstrings
- Document parameters, return values, and exceptions
- Keep docstrings up to date with code changes

### Building Documentation

```bash
# Serve documentation locally
mkdocs serve

# Build documentation
mkdocs build

# Deploy documentation (maintainers only)
mkdocs gh-deploy
```

## Pull Request Process

1. **Ensure all tests pass**:
   ```bash
   pytest
   ```

2. **Ensure code passes linting**:
   ```bash
   ruff check alpha_evolve/ tests/
   ```

3. **Update documentation** for any changed functionality

4. **Update CHANGELOG.md** with your changes

5. **Fill out the PR template** with:
   - Description of changes
   - Related issues
   - Type of change (bug fix, feature, breaking change)
   - Testing performed
   - Screenshots (if applicable)

6. **Request review** from maintainers

7. **Address review feedback** promptly

8. **Squash commits** if requested before merge

### PR Title Format

Use conventional commit format:
- `feat: description` - New feature
- `fix: description` - Bug fix
- `docs: description` - Documentation changes
- `test: description` - Test changes
- `refactor: description` - Code refactoring
- `chore: description` - Maintenance tasks

### Review Process

- At least one maintainer approval required
- All CI checks must pass
- No unresolved conversations
- Code review feedback addressed

## Release Process

(For maintainers)

1. **Update version** in `pyproject.toml`
2. **Update CHANGELOG.md** with release notes
3. **Create release branch**: `release/vX.Y.Z`
4. **Run full test suite** and verify
5. **Create GitHub release** with tag `vX.Y.Z`
6. **GitHub Actions** will automatically:
   - Build and test
   - Publish to PyPI
   - Build and push Docker image

## Questions?

- Open an issue for questions
- Join our discussions
- Check existing documentation

Thank you for contributing to AlphaEvolve!
