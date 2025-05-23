# Running Evolution

This guide covers how to configure and execute evolution experiments with AlphaEvolve.

## Basic Evolution

### Quick Start

```bash
# Initialize a new evolution project
alphaevolve setup my_evolution

# Run evolution with default settings
alphaevolve evolve --target my_program.py --evaluator my_evaluator.py
```

### Configuration File

Create an `evolution_config.yaml` file for better control:

```yaml
# evolution_config.yaml
target_program: "src/algorithm.py"
evaluator: "evaluators/test_evaluator.py"

# Evolution parameters
population_size: 50
max_generations: 100
elite_size: 10

# LLM configuration
llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.7
  max_tokens: 2000

# MAP-Elites configuration
map_elites:
  behavior_dimensions: 3
  archive_size: 1000
  
# Performance settings
parallel_evaluations: 4
timeout_seconds: 30
```

Then run:

```bash
alphaevolve evolve --config evolution_config.yaml
```

## Command Line Options

### Basic Options

```bash
# Specify target program and evaluator
alphaevolve evolve --target program.py --evaluator eval.py

# Use configuration file
alphaevolve evolve --config config.yaml

# Set population size
alphaevolve evolve --population-size 100

# Set maximum generations
alphaevolve evolve --max-generations 200
```

### Monitoring Options

```bash
# Enable real-time monitoring
alphaevolve evolve --monitor

# Set monitoring interval (seconds)
alphaevolve evolve --monitor --monitor-interval 5

# Save detailed logs
alphaevolve evolve --log-level debug --log-file evolution.log
```

### Checkpoint Options

```bash
# Enable automatic checkpointing
alphaevolve evolve --checkpoint-interval 10

# Resume from checkpoint
alphaevolve evolve --resume checkpoints/generation_50.json

# Specify checkpoint directory
alphaevolve evolve --checkpoint-dir ./my_checkpoints
```

## Configuration Options

### Evolution Parameters

```yaml
# Population and selection
population_size: 50              # Number of individuals in population
elite_size: 10                   # Number of elite individuals to preserve
max_generations: 100             # Maximum number of generations
early_stopping_patience: 20      # Stop if no improvement for N generations

# Mutation parameters
mutation_rate: 0.8               # Probability of mutation per individual
crossover_rate: 0.2              # Probability of crossover
tournament_size: 3               # Size of tournament selection

# Diversity parameters
novelty_threshold: 0.1           # Minimum distance for novelty
behavioral_diversity_weight: 0.3  # Weight for behavioral diversity
```

### LLM Configuration

```yaml
llm:
  # Provider options: openai, anthropic, local, mock
  provider: "openai"
  model: "gpt-4"
  
  # Generation parameters
  temperature: 0.7               # Creativity level (0.0-1.0)
  max_tokens: 2000              # Maximum tokens per response
  top_p: 0.9                    # Nucleus sampling parameter
  
  # Rate limiting
  requests_per_minute: 60
  max_retries: 3
  retry_delay: 1.0
  
  # API configuration
  api_key_env: "OPENAI_API_KEY"  # Environment variable for API key
  base_url: null                 # Custom API endpoint (optional)
```

### Performance Settings

```yaml
# Parallel processing
parallel_evaluations: 4          # Number of parallel evaluation processes
parallel_llm_calls: 2           # Number of parallel LLM requests

# Timeouts
evaluation_timeout: 30           # Seconds to timeout evaluation
llm_timeout: 60                 # Seconds to timeout LLM calls
program_execution_timeout: 10    # Seconds to timeout program execution

# Memory management
max_memory_usage: "4GB"         # Maximum memory per process
garbage_collection_interval: 100 # Generations between GC
```

## Advanced Configuration

### Custom Prompt Templates

```yaml
prompts:
  mutation_template: |
    Improve this code to optimize for {objectives}.
    
    Current code:
    ```python
    {current_code}
    ```
    
    Evaluation feedback:
    {feedback}
    
    Generate an improved version that maintains the same interface.
    
  crossover_template: |
    Combine the best aspects of these two code implementations:
    
    Version A:
    ```python
    {code_a}
    ```
    
    Version B:
    ```python
    {code_b}
    ```
    
    Create a hybrid that combines their strengths.
```

### Behavioral Dimension Configuration

```yaml
map_elites:
  behavior_dimensions: 3
  dimension_ranges:
    - name: "efficiency"
      min: 0.0
      max: 1.0
      bins: 20
    - name: "complexity"
      min: 0.0
      max: 100.0
      bins: 15
    - name: "novelty"
      min: 0.0
      max: 1.0
      bins: 10
      
  archive_size: 1000
  replacement_strategy: "fitness_based"  # Options: fitness_based, random, oldest
```

### Evaluation Configuration

```yaml
evaluation:
  # Test case configuration
  test_cases_file: "tests/test_cases.json"
  dynamic_test_generation: true
  test_difficulty_progression: true
  
  # Evaluation strategy
  strategy: "comprehensive"        # Options: basic, comprehensive, progressive
  min_test_cases: 10
  max_test_cases: 100
  
  # Fitness aggregation
  fitness_aggregation: "mean"     # Options: mean, min, max, weighted
  weights: [0.4, 0.3, 0.2, 0.1]  # Weights for multiple objectives
```

## Running Experiments

### Single Evolution Run

```bash
# Basic evolution
alphaevolve evolve \
  --target examples/sorting_algorithm.py \
  --evaluator examples/sorting_evaluator.py \
  --population-size 50 \
  --max-generations 100 \
  --monitor
```

### Batch Experiments

Create a batch configuration file:

```yaml
# batch_config.yaml
experiments:
  - name: "small_population"
    config:
      population_size: 25
      max_generations: 200
      
  - name: "large_population"
    config:
      population_size: 100
      max_generations: 100
      
  - name: "high_mutation"
    config:
      population_size: 50
      mutation_rate: 0.9
      temperature: 0.9

base_config: "evolution_config.yaml"
output_dir: "results/batch_experiment"
```

Run batch experiments:

```bash
alphaevolve batch --config batch_config.yaml --parallel 3
```

### Distributed Evolution

For large-scale experiments across multiple machines:

```yaml
# distributed_config.yaml
distributed:
  mode: "coordinator"  # Options: coordinator, worker
  workers: 4
  coordinator_host: "localhost"
  coordinator_port: 8080
  
  # Work distribution
  evaluation_workers: 2
  llm_workers: 2
  
  # Communication
  heartbeat_interval: 30
  timeout: 300
```

Start coordinator:

```bash
alphaevolve evolve --config distributed_config.yaml --distributed
```

Start workers on other machines:

```bash
alphaevolve worker --coordinator localhost:8080 --worker-type evaluation
alphaevolve worker --coordinator localhost:8080 --worker-type llm
```

## Monitoring and Analysis

### Real-time Monitoring

```bash
# Enable terminal monitoring
alphaevolve evolve --monitor

# Web-based monitoring
alphaevolve evolve --web-monitor --port 8080
```

### Progress Tracking

Monitor key metrics during evolution:

- **Best fitness**: Highest fitness in current population
- **Average fitness**: Population mean fitness
- **Diversity**: Behavioral diversity measures
- **Archive size**: Number of unique solutions found
- **LLM success rate**: Percentage of successful LLM calls

### Checkpoint Management

```bash
# List available checkpoints
alphaevolve checkpoints list

# Resume from specific checkpoint
alphaevolve evolve --resume checkpoints/generation_75.json

# Create manual checkpoint
alphaevolve checkpoints create --output manual_checkpoint.json
```

## Troubleshooting

### Common Issues

#### Evolution Stagnates

```yaml
# Increase diversity
map_elites:
  behavioral_diversity_weight: 0.5
  novelty_threshold: 0.05

# Increase mutation rate
mutation_rate: 0.9
temperature: 0.8
```

#### LLM Calls Fail

```yaml
# Increase retry limits
llm:
  max_retries: 5
  retry_delay: 2.0
  timeout: 120

# Use fallback model
llm:
  fallback_model: "gpt-3.5-turbo"
  fallback_temperature: 0.5
```

#### Memory Issues

```yaml
# Reduce parallelism
parallel_evaluations: 2
parallel_llm_calls: 1

# Enable aggressive garbage collection
garbage_collection_interval: 50
max_memory_usage: "2GB"
```

#### Slow Evaluation

```yaml
# Optimize evaluation
evaluation:
  strategy: "basic"
  max_test_cases: 50
  
# Increase timeouts
evaluation_timeout: 60
program_execution_timeout: 20
```

### Debug Mode

Run with detailed debugging:

```bash
alphaevolve evolve \
  --config config.yaml \
  --log-level debug \
  --log-file debug.log \
  --save-intermediate \
  --no-cleanup
```

This saves all intermediate files and provides detailed logging for troubleshooting.

## Next Steps

- [Monitor evolution progress](monitoring.md)
- [Manage checkpoints and results](checkpoints.md)
- [Analyze and export results](../examples/analysis-tutorial.md)