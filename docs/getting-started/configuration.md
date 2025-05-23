# Configuration

AlphaEvolve uses a flexible configuration system that supports YAML files, JSON files, and environment variables. This guide explains how to configure AlphaEvolve for your specific needs.

## Quick Configuration

The fastest way to get started is using the setup command:

```bash
# Basic configuration (mock LLMs, no API keys needed)
alphaevolve setup --template basic

# Research configuration (real LLMs, requires API keys)
alphaevolve setup --template research

# Production configuration (full security, logging, fallbacks)
alphaevolve setup --template production
```

This creates an `alphaevolve.yaml` file in your current directory.

## Configuration File Format

AlphaEvolve supports both YAML and JSON configuration files:

=== "YAML (Recommended)"

    ```yaml title="alphaevolve.yaml"
    project_name: "My Evolution Project"
    environment: "development"
    
    llm:
      default_provider: "openai"
      fallback_provider: "anthropic"
      providers:
        openai:
          model: "gpt-4"
          api_key: "${OPENAI_API_KEY}"
          temperature: 0.2
        anthropic:
          model: "claude-3-sonnet-20240229"
          api_key: "${ANTHROPIC_API_KEY}"
          temperature: 0.2
    
    sandbox:
      enabled: true
      type: "docker"
      timeout_seconds: 30
      memory_limit: "256m"
    
    evolution:
      population_size: 50
      max_generations: 100
    ```

=== "JSON"

    ```json title="alphaevolve.json"
    {
      "project_name": "My Evolution Project",
      "environment": "development",
      "llm": {
        "default_provider": "openai",
        "fallback_provider": "anthropic",
        "providers": {
          "openai": {
            "model": "gpt-4",
            "api_key": "${OPENAI_API_KEY}",
            "temperature": 0.2
          }
        }
      },
      "sandbox": {
        "enabled": true,
        "type": "docker"
      }
    }
    ```

## Configuration Locations

AlphaEvolve searches for configuration files in this order:

1. File specified with `--config` flag
2. `alphaevolve.yaml` in current directory
3. `alphaevolve.yml` in current directory
4. `config/alphaevolve.yaml` in current directory
5. `~/.alphaevolve/config.yaml` in home directory

## Environment Variables

You can override any configuration value using environment variables with the `ALPHAEVOLVE_` prefix:

```bash
# Override LLM provider
export ALPHAEVOLVE_LLM__DEFAULT_PROVIDER=anthropic

# Override sandbox settings
export ALPHAEVOLVE_SANDBOX__ENABLED=false
export ALPHAEVOLVE_SANDBOX__TYPE=process

# Override evolution parameters
export ALPHAEVOLVE_EVOLUTION__POPULATION_SIZE=100
export ALPHAEVOLVE_EVOLUTION__MAX_GENERATIONS=200
```

Use double underscores (`__`) to access nested configuration values.

## Configuration Sections

### Project Settings

Basic project information and environment settings:

```yaml
project_name: "Algorithm Optimization Project"
version: "1.0.0"
environment: "development"  # development, staging, production
debug: false
```

### LLM Configuration

Configure language model providers and their settings:

```yaml
llm:
  default_provider: "openai"           # Primary LLM to use
  fallback_provider: "anthropic"      # Fallback if primary fails
  
  providers:
    openai:
      model: "gpt-4"                   # Model name
      api_key: "${OPENAI_API_KEY}"     # API key (use env var)
      base_url: null                   # Custom API base URL
      temperature: 0.2                 # Sampling temperature (0.0-2.0)
      max_tokens: 2000                 # Maximum tokens to generate
      timeout_seconds: 30              # Request timeout
      rate_limit_rpm: 60               # Requests per minute limit
    
    anthropic:
      model: "claude-3-sonnet-20240229"
      api_key: "${ANTHROPIC_API_KEY}"
      temperature: 0.2
      max_tokens: 2000
      timeout_seconds: 30
      rate_limit_rpm: 60
    
    mock:
      model: "mock-model"              # For testing without API keys
      # No API key needed for mock provider
```

### Sandbox Configuration

Configure secure code execution environments:

```yaml
sandbox:
  enabled: true                        # Enable sandboxing
  type: "docker"                       # "docker" or "process"
  
  # Resource limits
  cpu_limit: 1.0                       # CPU cores limit
  memory_limit: "256m"                 # Memory limit (e.g., "256m", "1g")
  timeout_seconds: 30                  # Execution timeout
  max_output_size: 1048576             # Max output size in bytes
  network_disabled: true               # Disable network access
  
  # Docker-specific settings
  docker_image: "python:3.12-slim"    # Docker image to use
  docker_pull_policy: "if_not_present" # Image pull policy
```

### Evolution Parameters

Control the evolutionary algorithm behavior:

```yaml
evolution:
  population_size: 50                  # Programs per generation
  max_generations: 100                 # Maximum generations to run
  elite_ratio: 0.1                     # Fraction of elites to keep
  
  # Selection and mutation
  selection_pressure: 2.0              # Selection pressure for parents
  mutation_rate: 0.1                   # Probability of mutation
  crossover_rate: 0.8                  # Probability of crossover
  
  # Parallel processing
  parallel_evaluations: 4              # Number of parallel workers
  batch_evaluation: true               # Batch evaluations for efficiency
  
  # Migration settings (for island model)
  migration_interval: 50               # Generations between migrations
  migration_size: 5                    # Individuals to migrate
```

### Database Configuration

Configure program storage and MAP-Elites archive:

```yaml
database:
  type: "memory"                       # "memory", "sqlite", "postgresql"
  connection_string: null              # Database connection string
  
  # MAP-Elites archive settings
  feature_dimensions:                  # Feature dimensions for archive
    - "complexity"
    - "performance"
  feature_bins: 10                     # Bins per feature dimension
  
  # Performance settings
  batch_size: 100                      # Batch size for operations
  connection_pool_size: 5              # Database connection pool
  
  # Persistence settings
  checkpoint_interval: 100             # Generations between checkpoints
  auto_save: true                      # Automatically save database
```

### Logging Configuration

Configure logging and monitoring:

```yaml
logging:
  level: "INFO"                        # Log level
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  
  # File logging
  file_enabled: true                   # Enable file logging
  file_path: "alphaevolve.log"         # Log file path
  file_max_size: "10MB"                # Maximum log file size
  file_backup_count: 5                 # Number of backup files
  
  # Console logging
  console_enabled: true                # Enable console logging
  console_level: "INFO"                # Console log level
  
  # Metrics and monitoring
  metrics_enabled: false               # Enable metrics collection
  metrics_port: 8000                   # Port for metrics server
```

### Security Configuration

Configure security and safety settings:

```yaml
security:
  # API key encryption
  encrypt_credentials: false           # Encrypt stored credentials
  encryption_key_path: null            # Path to encryption key
  
  # Sandbox security
  strict_sandbox: true                 # Use strict sandboxing
  allowed_imports:                     # Allowed Python imports
    - "math"
    - "random"
    - "json"
    - "re"
    - "datetime"
  blocked_functions:                   # Blocked Python functions
    - "exec"
    - "eval"
    - "compile"
    - "__import__"
  
  # Network security
  allowed_domains: []                  # Allowed domains for requests
```

## Configuration Templates

### Basic Template

For getting started and testing:

```yaml
project_name: "AlphaEvolve Project"
llm:
  default_provider: "mock"             # No API keys needed
sandbox:
  enabled: true
  type: "process"                      # No Docker required
evolution:
  population_size: 20                  # Small population for speed
  max_generations: 10
```

### Research Template

For research and experimentation:

```yaml
project_name: "Research Project"
llm:
  default_provider: "openai"
  providers:
    openai:
      model: "gpt-4"
      api_key: "${OPENAI_API_KEY}"
    anthropic:
      model: "claude-3-sonnet-20240229"
      api_key: "${ANTHROPIC_API_KEY}"
sandbox:
  enabled: true
  type: "docker"                       # Enhanced security
evolution:
  population_size: 100                 # Larger population
  max_generations: 1000
```

### Production Template

For production deployments:

```yaml
project_name: "Production System"
environment: "production"
llm:
  default_provider: "anthropic"
  fallback_provider: "openai"
  providers:
    anthropic:
      model: "claude-3-sonnet-20240229"
      api_key: "${ANTHROPIC_API_KEY}"
      rate_limit_rpm: 100
    openai:
      model: "gpt-4"
      api_key: "${OPENAI_API_KEY}"
      rate_limit_rpm: 60
sandbox:
  enabled: true
  type: "docker"
  strict_sandbox: true
security:
  encrypt_credentials: true
  strict_sandbox: true
logging:
  level: "INFO"
  file_enabled: true
  metrics_enabled: true
```

## Validation and Testing

Check your configuration for errors:

```bash
# Validate configuration
alphaevolve status

# Test with specific config file
alphaevolve --config my-config.yaml status

# Check LLM connectivity
alphaevolve --config production.yaml status
```

## Environment-Specific Configuration

Use different configurations for different environments:

```bash
# Development
alphaevolve --config config/development.yaml evolve --source code.py

# Staging
alphaevolve --config config/staging.yaml evolve --source code.py

# Production
alphaevolve --config config/production.yaml evolve --source code.py
```

## Best Practices

### Security

1. **Never commit API keys** to version control
2. **Use environment variables** for sensitive data
3. **Enable sandboxing** in production environments
4. **Limit resource usage** to prevent system overload

### Performance

1. **Adjust population size** based on available resources
2. **Use Docker sandboxing** for better isolation
3. **Enable parallel evaluation** for faster processing
4. **Configure rate limits** to avoid API throttling

### Reliability

1. **Configure fallback providers** for redundancy
2. **Enable checkpointing** for long experiments
3. **Set appropriate timeouts** to prevent hangs
4. **Monitor logs** for errors and warnings

## Troubleshooting

### Common Configuration Issues

**Invalid YAML Syntax**
```
Error: YAML syntax error
```
Solution: Validate YAML syntax using a YAML linter.

**Missing API Keys**
```
Error: API key not found for provider 'openai'
```
Solution: Set environment variables or add keys to configuration.

**Permission Errors**
```
Error: Cannot write to log file
```
Solution: Check file permissions and directory access.

**Docker Not Available**
```
Warning: Docker not found, falling back to process sandbox
```
Solution: Install Docker or change sandbox type to "process".

### Getting Help

For configuration issues:

1. Check the [troubleshooting guide](../user-guide/troubleshooting.md)
2. Validate your configuration with `alphaevolve status`
3. Check logs for detailed error messages
4. Ask for help in [GitHub Discussions](https://github.com/alphaevolve/alphaevolve/discussions)