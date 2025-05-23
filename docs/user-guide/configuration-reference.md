# Configuration Reference

This comprehensive reference covers all configuration options available in AlphaEvolve.

## Configuration File Format

AlphaEvolve supports both YAML and JSON configuration formats:

```yaml
# evolution_config.yaml
target_program: "src/algorithm.py"
evaluator: "evaluators/my_evaluator.py"

evolution:
  population_size: 50
  max_generations: 100

llm:
  provider: "openai"
  model: "gpt-4"
```

```json
{
  "target_program": "src/algorithm.py",
  "evaluator": "evaluators/my_evaluator.py",
  "evolution": {
    "population_size": 50,
    "max_generations": 100
  },
  "llm": {
    "provider": "openai", 
    "model": "gpt-4"
  }
}
```

## Core Configuration

### Target Program and Evaluator

```yaml
# Required: Main program file containing evolvable code
target_program: "path/to/program.py"

# Required: Evaluation function file  
evaluator: "path/to/evaluator.py"

# Optional: Working directory for evolution
working_directory: "./evolution_workspace"

# Optional: Additional Python paths
python_paths:
  - "./src"
  - "./lib"
  - "/usr/local/lib/python3.9/site-packages"
```

### Basic Evolution Parameters

```yaml
evolution:
  # Population and generations
  population_size: 50                    # Number of individuals (default: 50)
  max_generations: 100                   # Maximum generations (default: 100)
  elite_size: 10                        # Elite individuals preserved (default: 10)
  
  # Early stopping
  early_stopping:
    enabled: true                        # Enable early stopping (default: true)
    patience: 20                         # Generations without improvement (default: 20)
    min_improvement: 0.001               # Minimum improvement threshold (default: 0.001)
    
  # Random seed for reproducibility  
  random_seed: 42                        # Fixed seed (default: random)
```

## LLM Configuration

### Provider Settings

```yaml
llm:
  provider: "openai"                     # Provider: openai, anthropic, local, mock
  model: "gpt-4"                         # Model name
  
  # Generation parameters
  temperature: 0.7                       # Creativity (0.0-1.0, default: 0.7)
  max_tokens: 2000                       # Max response tokens (default: 2000)
  top_p: 0.9                            # Nucleus sampling (default: 0.9)
  top_k: 50                             # Top-k sampling (default: 50)
  frequency_penalty: 0.0                 # Frequency penalty (default: 0.0)
  presence_penalty: 0.0                  # Presence penalty (default: 0.0)
  
  # API configuration
  api_key_env: "OPENAI_API_KEY"         # Environment variable for API key
  base_url: null                         # Custom API endpoint (optional)
  organization: null                     # Organization ID (optional)
  
  # Rate limiting and retries
  requests_per_minute: 60                # Rate limit (default: 60)
  max_retries: 3                        # Retry attempts (default: 3)
  retry_delay: 1.0                      # Base retry delay seconds (default: 1.0)
  backoff_factor: 2.0                   # Exponential backoff (default: 2.0)
  timeout: 60                           # Request timeout seconds (default: 60)
  
  # Fallback configuration
  fallback:
    enabled: true                        # Enable fallback model (default: false)
    model: "gpt-3.5-turbo"              # Fallback model
    temperature: 0.5                     # Fallback temperature
    max_tokens: 1000                     # Fallback max tokens
```

### Provider-Specific Settings

#### OpenAI Configuration

```yaml
llm:
  provider: "openai"
  model: "gpt-4"                         # gpt-4, gpt-4-turbo, gpt-3.5-turbo
  
  # OpenAI-specific parameters
  logit_bias: {}                         # Token bias (optional)
  user: "alphaevolve_user"              # User identifier (optional)
  
  # Fine-tuned model support
  fine_tuned_model: "ft:gpt-3.5-turbo:org:model:id"  # Optional
```

#### Anthropic Configuration

```yaml
llm:
  provider: "anthropic"
  model: "claude-3-sonnet-20240229"      # Claude model
  
  # Anthropic-specific parameters
  system_prompt: "You are a code optimization expert."
  stop_sequences: ["Human:", "Assistant:"]
```

#### Local Model Configuration

```yaml
llm:
  provider: "local"
  model: "codellama"                     # Local model name
  
  # Local server configuration
  base_url: "http://localhost:8080"      # Local API endpoint
  
  # Model-specific parameters
  context_length: 4096                   # Context window size
  gpu_layers: 32                         # GPU acceleration layers
  threads: 8                            # CPU threads
```

## Evolution Algorithm Configuration

### Selection and Mutation

```yaml
evolution:
  # Selection strategy
  selection:
    strategy: "tournament"               # tournament, roulette, rank, elitist
    tournament_size: 3                   # Tournament selection size (default: 3)
    selection_pressure: 1.5              # Selection pressure (default: 1.5)
    
  # Mutation parameters
  mutation:
    rate: 0.8                           # Mutation probability (default: 0.8)
    strategy: "llm_guided"              # llm_guided, random, template_based
    
    # LLM-guided mutation
    llm_guided:
      context_window: 1000               # Context chars for LLM (default: 1000)
      include_feedback: true             # Include evaluation feedback (default: true)
      diversity_weight: 0.3              # Weight for diversity promotion (default: 0.3)
      
  # Crossover parameters  
  crossover:
    rate: 0.2                           # Crossover probability (default: 0.2)
    strategy: "llm_hybrid"              # llm_hybrid, template_based, semantic
    max_parents: 2                      # Maximum parents per crossover (default: 2)
```

### MAP-Elites Configuration

```yaml
map_elites:
  # Archive settings
  archive_size: 1000                     # Maximum archive size (default: 1000)
  behavior_dimensions: 3                 # Number of behavioral dimensions (auto-detected)
  
  # Dimension configuration
  dimensions:
    - name: "efficiency"                 # Dimension name
      min: 0.0                          # Minimum value
      max: 1.0                          # Maximum value  
      bins: 20                          # Number of bins
      type: "continuous"                # continuous, discrete
      
    - name: "complexity"
      min: 0.0
      max: 100.0
      bins: 15
      type: "continuous"
      
    - name: "novelty"
      min: 0.0
      max: 1.0
      bins: 10
      type: "continuous"
      
  # Archive management
  replacement_strategy: "fitness_based"  # fitness_based, random, oldest
  novelty_threshold: 0.1                # Minimum distance for novelty (default: 0.1)
  behavioral_diversity_weight: 0.3       # Weight for behavioral diversity (default: 0.3)
```

## Evaluation Configuration

### Test Case Management

```yaml
evaluation:
  # Test case configuration
  test_cases:
    source: "file"                       # file, generator, hybrid
    file_path: "tests/test_cases.json"   # Path to test cases file
    
    # Dynamic test generation
    dynamic_generation:
      enabled: true                      # Enable dynamic test generation (default: false)
      strategy: "progressive"            # progressive, random, adaptive
      min_cases: 10                     # Minimum test cases (default: 10)
      max_cases: 100                    # Maximum test cases (default: 100)
      difficulty_progression: true       # Increase difficulty over time (default: true)
      
  # Evaluation strategy
  strategy: "comprehensive"              # basic, comprehensive, progressive
  
  # Fitness aggregation
  fitness_aggregation: "mean"            # mean, min, max, weighted, harmonic_mean
  aggregation_weights: [0.4, 0.3, 0.2, 0.1]  # Weights for weighted aggregation
  
  # Timeout and resource limits
  timeout: 30                           # Evaluation timeout seconds (default: 30)
  memory_limit: "1GB"                   # Memory limit per evaluation (default: 1GB)
  
  # Parallel evaluation
  parallel_evaluations: 4               # Number of parallel processes (default: 4)
  batch_size: 10                       # Evaluations per batch (default: 10)
```

### Custom Evaluation Functions

```yaml
evaluation:
  # Custom evaluator configuration
  custom_evaluator:
    module: "custom_evaluators"         # Python module
    function: "advanced_evaluator"      # Function name
    
    # Custom parameters
    parameters:
      weight_accuracy: 0.5
      weight_efficiency: 0.3
      weight_novelty: 0.2
      
  # Multi-objective evaluation
  multi_objective:
    enabled: false                      # Enable multi-objective optimization
    objectives: ["accuracy", "speed", "simplicity"]
    weights: [0.5, 0.3, 0.2]
    pareto_ranking: true               # Use Pareto ranking
```

## Performance Configuration

### Parallel Processing

```yaml
performance:
  # Process pools
  parallel_evaluations: 4               # Evaluation worker processes (default: 4)
  parallel_llm_calls: 2                # Parallel LLM requests (default: 2)
  parallel_mutations: 1                 # Parallel mutation processes (default: 1)
  
  # Thread pools  
  evaluation_threads: 2                 # Threads per evaluation process (default: 2)
  llm_threads: 1                       # Threads per LLM process (default: 1)
  
  # Memory management
  max_memory_per_process: "2GB"         # Memory limit per process
  garbage_collection:
    enabled: true                       # Enable periodic GC (default: true)
    interval: 50                       # GC every N generations (default: 50)
    aggressive: false                   # Aggressive GC mode (default: false)
    
  # Caching
  cache:
    enabled: true                       # Enable result caching (default: true)
    max_size: 1000                     # Maximum cached results (default: 1000)
    ttl: 3600                          # Cache TTL seconds (default: 3600)
```

### Timeouts and Limits

```yaml
performance:
  timeouts:
    program_execution: 10               # Program execution timeout (default: 10)
    evaluation_total: 30                # Total evaluation timeout (default: 30)
    llm_request: 60                    # LLM request timeout (default: 60)
    generation_max: 3600               # Maximum generation time (default: 3600)
    
  limits:
    max_code_length: 10000             # Maximum code length chars (default: 10000)
    max_llm_tokens: 4000               # Maximum LLM input tokens (default: 4000)
    max_output_size: "10MB"            # Maximum program output size
    max_file_handles: 1000             # Maximum open file handles
```

## Monitoring Configuration

### Logging

```yaml
logging:
  # Basic logging
  level: "INFO"                         # DEBUG, INFO, WARNING, ERROR
  file: "evolution.log"                 # Log file path (default: evolution.log)
  console: true                         # Log to console (default: true)
  
  # Log rotation
  max_size: "100MB"                     # Maximum log file size (default: 100MB)
  backup_count: 5                       # Number of backup files (default: 5)
  rotation: "size"                      # size, time, both
  
  # Log formatting
  format: "[{timestamp}] {level} | {component} | {message}"
  timestamp_format: "%Y-%m-%d %H:%M:%S"
  
  # Component-specific logging
  components:
    controller: "INFO"                  # Main controller
    llm_interface: "DEBUG"              # LLM interactions
    evaluation_engine: "INFO"           # Evaluation system
    diff_applier: "WARNING"             # Code application
    program_database: "INFO"            # Database operations
    
  # Structured logging
  structured: false                     # Enable structured logging (default: false)
  output_format: "text"                # text, json
```

### Real-time Monitoring

```yaml
monitoring:
  # Terminal monitoring
  terminal:
    enabled: true                       # Enable terminal monitoring (default: true)
    update_interval: 5                  # Update interval seconds (default: 5)
    show_progress_bar: true            # Show progress bar (default: true)
    compact_mode: false                # Compact display mode (default: false)
    
  # Web dashboard
  web:
    enabled: false                      # Enable web dashboard (default: false)
    port: 8080                         # Dashboard port (default: 8080)
    host: "0.0.0.0"                   # Bind host (default: 0.0.0.0)
    auto_open: true                    # Auto-open browser (default: true)
    
  # Metrics collection
  metrics:
    collect_system_metrics: true        # Collect CPU/memory stats (default: true)
    collect_llm_metrics: true          # Collect LLM performance (default: true)
    collect_timing_metrics: true       # Collect timing data (default: true)
    
    # Custom metrics
    custom_collectors: []               # List of custom metric collectors
```

## Checkpointing Configuration

### Automatic Checkpoints

```yaml
checkpointing:
  # Basic settings
  enabled: true                         # Enable checkpointing (default: true)
  interval: 10                         # Checkpoint every N generations (default: 10)
  directory: "checkpoints"              # Checkpoint directory (default: checkpoints)
  
  # Retention policy
  max_checkpoints: 20                   # Maximum checkpoints to keep (default: 20)
  keep_best: true                       # Always keep best checkpoint (default: true)
  keep_milestones: [25, 50, 100, 200]  # Always keep these generations
  
  # Compression
  compress: true                        # Compress checkpoints (default: true)
  compression_level: 6                  # Compression level 1-9 (default: 6)
  compression_algorithm: "gzip"         # gzip, bz2, lzma
  
  # Backup and sync
  backup:
    enabled: false                      # Enable backup (default: false)
    directory: "./backup_checkpoints"   # Backup directory
    cloud_sync: false                  # Sync to cloud storage (default: false)
    
  # Verification
  verify_on_create: true               # Verify after creation (default: true)
  verify_on_restore: true              # Verify before restore (default: true)
```

### Cloud Backup

```yaml
checkpointing:
  cloud_backup:
    enabled: false                      # Enable cloud backup (default: false)
    provider: "s3"                     # s3, gcs, azure, dropbox
    
    # S3 configuration
    s3:
      bucket: "my-evolution-checkpoints"
      region: "us-west-2"
      access_key_env: "AWS_ACCESS_KEY_ID"
      secret_key_env: "AWS_SECRET_ACCESS_KEY"
      prefix: "experiments/alphaevolve"
      
    # Upload settings
    sync_interval: 300                  # Sync every 5 minutes
    encryption: true                    # Encrypt before upload
    compression: true                   # Compress before upload
```

## Advanced Configuration

### Custom Prompt Templates

```yaml
prompts:
  # Mutation prompt template
  mutation_template: |
    You are an expert code optimizer. Improve this code to optimize for: {objectives}
    
    Current code:
    ```python
    {current_code}
    ```
    
    Evaluation feedback:
    - Fitness: {fitness}
    - Efficiency: {efficiency}
    - Complexity: {complexity}
    
    Generate an improved version that maintains the same interface but optimizes the specified objectives.
    
  # Crossover prompt template  
  crossover_template: |
    Combine the best aspects of these two code implementations:
    
    Implementation A (fitness: {fitness_a}):
    ```python
    {code_a}
    ```
    
    Implementation B (fitness: {fitness_b}):
    ```python  
    {code_b}
    ```
    
    Create a hybrid implementation that combines their strengths.
    
  # Custom templates
  custom_templates:
    optimization_focused: |
      Focus on performance optimization for this code...
    readability_focused: |
      Improve code readability while maintaining functionality...
```

### Experimental Features

```yaml
experimental:
  # Advanced evolution strategies
  adaptive_mutation_rate: false          # Adapt mutation rate based on progress
  meta_evolution: false                  # Evolve evolution parameters
  co_evolution: false                    # Co-evolve test cases and code
  
  # Advanced LLM features
  llm_ensemble: false                    # Use multiple LLM models
  dynamic_prompting: false               # Adapt prompts based on context
  llm_fine_tuning: false                # Fine-tune models during evolution
  
  # Novel algorithms
  quality_diversity: false               # Quality-diversity optimization
  map_elites_variants:
    cvt_map_elites: false               # CVT-MAP-Elites
    mega_map_elites: false              # MEGA-MAP-Elites
    
  # Research features
  behavioral_analysis: false             # Deep behavioral analysis
  code_similarity_analysis: false       # Analyze code similarity patterns
  evolution_visualization: false        # Advanced visualization tools
```

## Environment Variables

AlphaEvolve recognizes these environment variables:

```bash
# LLM API Keys
export OPENAI_API_KEY="your_openai_key"
export ANTHROPIC_API_KEY="your_anthropic_key"

# Configuration override
export ALPHAEVOLVE_CONFIG="config.yaml"
export ALPHAEVOLVE_LOG_LEVEL="DEBUG"
export ALPHAEVOLVE_WORKSPACE="./workspace"

# Performance tuning
export ALPHAEVOLVE_PARALLEL_EVALUATIONS="8"
export ALPHAEVOLVE_MAX_MEMORY="4GB"

# Cloud storage
export AWS_ACCESS_KEY_ID="your_aws_key"
export AWS_SECRET_ACCESS_KEY="your_aws_secret"

# Custom paths
export PYTHONPATH="./src:./lib:$PYTHONPATH"
```

## Configuration Templates

AlphaEvolve provides several built-in configuration templates:

### Basic Template

```bash
alphaevolve setup --template basic
```

```yaml
# Basic configuration for simple experiments
target_program: "program.py"
evaluator: "evaluator.py"

evolution:
  population_size: 20
  max_generations: 50

llm:
  provider: "openai"
  model: "gpt-3.5-turbo"
  temperature: 0.7
```

### Research Template

```bash
alphaevolve setup --template research
```

```yaml
# Research configuration with comprehensive monitoring
target_program: "research_program.py"
evaluator: "research_evaluator.py"

evolution:
  population_size: 100
  max_generations: 500
  
monitoring:
  web:
    enabled: true
  metrics:
    collect_system_metrics: true
    
checkpointing:
  interval: 25
  max_checkpoints: 50
```

### Production Template

```bash
alphaevolve setup --template production
```

```yaml
# Production configuration with reliability features
target_program: "production_program.py"
evaluator: "production_evaluator.py"

evolution:
  population_size: 50
  max_generations: 200
  
performance:
  parallel_evaluations: 8
  max_memory_per_process: "2GB"
  
checkpointing:
  enabled: true
  interval: 10
  cloud_backup:
    enabled: true
```

## Configuration Validation

AlphaEvolve automatically validates configuration files:

```bash
# Validate configuration
alphaevolve config validate evolution_config.yaml

# Check for common issues
alphaevolve config check evolution_config.yaml

# Generate configuration documentation
alphaevolve config docs --output config_docs.html
```

## Best Practices

### Configuration Organization

1. **Use version control**: Track configuration changes
2. **Modular configs**: Split large configs into modules
3. **Environment-specific**: Separate dev/prod configurations
4. **Documentation**: Comment complex configuration sections
5. **Validation**: Always validate before running experiments

### Performance Optimization

1. **Right-size resources**: Match parallelism to hardware
2. **Monitor memory**: Set appropriate memory limits
3. **Cache effectively**: Enable caching for repeated evaluations
4. **Checkpoint wisely**: Balance safety vs. storage costs

### Security Considerations

1. **API keys**: Use environment variables, never hardcode
2. **File permissions**: Secure checkpoint and log files
3. **Cloud access**: Use IAM roles instead of access keys
4. **Validation**: Validate all external inputs

## Next Steps

- [See complete examples](../examples/basic-optimization.md)
- [Learn about advanced features](../advanced/distributed-evolution.md)
- [Explore the API reference](../api-reference/core-modules.md)