# AlphaEvolve

**Evolutionary Code Optimization with Large Language Models**

AlphaEvolve is a cutting-edge framework that combines evolutionary algorithms with Large Language Models (LLMs) to automatically optimize and evolve code. By leveraging the power of MAP-Elites diversity-based selection and state-of-the-art language models, AlphaEvolve can discover novel algorithmic solutions while maintaining population diversity.

## Key Features

**Evolutionary Optimization**
: Automatically evolves code blocks using MAP-Elites algorithm for diversity-based selection

**LLM Integration**
: Supports OpenAI GPT and Anthropic Claude models for intelligent code generation

**Secure Execution**
: Docker and process-based sandboxing ensures safe evaluation of generated code

**Interactive CLI**
: Rich terminal interface with real-time progress monitoring and beautiful visualizations

**Persistent Storage**
: Comprehensive checkpointing system allows resuming long-running experiments

**Professional Configuration**
: YAML/JSON configuration with environment variable support and validation

## Quick Start

Install AlphaEvolve and run your first evolution experiment:

```bash
# Install AlphaEvolve
pip install alphaevolve

# Set up configuration
alphaevolve setup --template research

# Create a simple test file
cat > my_algorithm.py << EOF
# EVOLVE-BLOCK-START optimization_target
def calculate_result(x, y):
    # This function will be evolved by AlphaEvolve
    return x * 2 + y * 3
# EVOLVE-BLOCK-END optimization_target
EOF

# Run evolution with interactive monitoring
alphaevolve evolve --source my_algorithm.py --generations 10 --interactive
```

## Use Cases

**Algorithm Optimization**
: Improve performance of existing algorithms by exploring alternative implementations

**Novel Discovery**
: Discover new algorithmic approaches that human programmers might not consider

**Performance Tuning**
: Automatically optimize code for specific performance metrics and constraints

**Research Applications**
: Study code evolution dynamics and explore the intersection of AI and software engineering

## Architecture Overview

AlphaEvolve consists of several interconnected components:

- **Task Definition & Code Parsing** - Identifies and extracts evolvable code blocks
- **Program Database** - Stores program variants using MAP-Elites archive structure  
- **LLM Interface** - Communicates with language models for code generation
- **Evaluation Engine** - Safely executes and evaluates code variants in sandboxed environments
- **Evolution Controller** - Orchestrates the evolutionary process and manages generations
- **Persistence System** - Provides checkpointing and data recovery capabilities

## Getting Started

Ready to start evolving code? Follow our comprehensive guides:

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Quick Start Guide**

    ---

    Get up and running with AlphaEvolve in minutes

    [:octicons-arrow-right-24: Getting Started](getting-started/quickstart.md)

-   :material-book-open:{ .lg .middle } **User Guide**

    ---

    Learn how to effectively use AlphaEvolve for your projects

    [:octicons-arrow-right-24: User Guide](user-guide/overview.md)

-   :material-code-braces:{ .lg .middle } **Examples**

    ---

    Explore real-world examples and use cases

    [:octicons-arrow-right-24: Examples](examples/algorithm-optimization.md)

-   :material-api:{ .lg .middle } **API Reference**

    ---

    Detailed documentation of all modules and functions

    [:octicons-arrow-right-24: API Reference](api-reference/task-utils.md)

</div>

## System Requirements

- **Python**: 3.12 or higher
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 1GB available space for evolution data
- **Docker**: Optional, for enhanced sandboxing security

## Community and Support

AlphaEvolve is an open-source project welcoming contributions from the community. Whether you're reporting bugs, suggesting features, or contributing code, your input helps make AlphaEvolve better.

- **GitHub**: [alphaevolve/alphaevolve](https://github.com/alphaevolve/alphaevolve)
- **Issues**: Report bugs and request features
- **Discussions**: Ask questions and share your experiences
- **Contributing**: See our [contribution guidelines](developer-guide/contributing.md)

## License

AlphaEvolve is released under the MIT License. See the [LICENSE](https://github.com/alphaevolve/alphaevolve/blob/main/LICENSE) file for details.