# Monitoring Evolution Progress

AlphaEvolve provides comprehensive monitoring tools to track evolution progress, analyze population dynamics, and optimize performance.

## Real-time Monitoring

### Terminal Monitoring

Enable terminal monitoring to see live progress updates:

```bash
alphaevolve evolve --config config.yaml --monitor
```

The terminal monitor displays:

```
Generation 25/100 | Best Fitness: 0.847 | Avg Fitness: 0.632 | Archive: 156/1000
├─ Population Diversity: 0.743
├─ LLM Success Rate: 89.2%
├─ Evaluation Time: 2.3s avg
└─ ETA: 15 minutes

Behavioral Dimensions:
├─ Efficiency: [0.12 ... 0.89] (mean: 0.54)
├─ Complexity: [1.2 ... 87.4] (mean: 23.7)  
└─ Novelty: [0.03 ... 0.95] (mean: 0.41)

Recent Best Programs:
├─ Generation 23: fitness=0.847, efficiency=0.82, complexity=12.3
├─ Generation 19: fitness=0.831, efficiency=0.71, complexity=25.1
└─ Generation 15: fitness=0.809, efficiency=0.64, complexity=18.9
```

### Web Dashboard

Launch a web-based monitoring dashboard:

```bash
alphaevolve evolve --config config.yaml --web-monitor --port 8080
```

Access the dashboard at `http://localhost:8080` to view:

- Real-time fitness plots
- Population diversity heatmaps
- Behavioral dimension distributions
- LLM performance metrics
- Interactive code diff viewer

## Monitoring Configuration

### Terminal Monitor Settings

```yaml
monitoring:
  terminal:
    enabled: true
    update_interval: 5          # Seconds between updates
    show_progress_bar: true
    show_population_stats: true
    show_behavioral_dims: true
    max_recent_programs: 5
    
    # Display options
    compact_mode: false         # Condensed display
    color_output: true          # Colored terminal output
    unicode_symbols: true       # Use Unicode symbols
```

### Web Monitor Settings

```yaml
monitoring:
  web:
    enabled: true
    port: 8080
    host: "0.0.0.0"            # Bind to all interfaces
    auto_open: true            # Open browser automatically
    
    # Data retention
    max_data_points: 1000      # Maximum points in plots
    update_frequency: 2        # Seconds between updates
    
    # Features
    enable_code_viewer: true
    enable_diff_viewer: true
    enable_export: true
```

## Key Metrics

### Fitness Metrics

**Best Fitness**: Highest fitness in the current population
```python
best_fitness = max(individual.fitness for individual in population)
```

**Average Fitness**: Mean fitness across all individuals
```python
avg_fitness = sum(individual.fitness for individual in population) / len(population)
```

**Fitness Improvement Rate**: Rate of fitness increase over generations
```python
improvement_rate = (current_best - previous_best) / generations_elapsed
```

### Population Diversity

**Behavioral Diversity**: Spread across behavioral dimensions
```python
behavioral_diversity = calculate_diversity_metric(behavioral_vectors)
```

**Genetic Diversity**: Variety in code implementations
```python
genetic_diversity = measure_code_similarity(population)
```

**Archive Utilization**: Percentage of archive slots filled
```python
archive_utilization = filled_slots / total_archive_size
```

### Performance Metrics

**LLM Success Rate**: Percentage of successful LLM calls
```python
llm_success_rate = successful_calls / total_calls * 100
```

**Evaluation Speed**: Average time per evaluation
```python
eval_speed = total_evaluation_time / number_of_evaluations
```

**Generation Time**: Time to complete each generation
```python
generation_time = sum(mutation_time, evaluation_time, selection_time)
```

## Logging Configuration

### Log Levels

```yaml
logging:
  level: "INFO"               # DEBUG, INFO, WARNING, ERROR
  file: "evolution.log"       # Log file path
  max_size: "100MB"          # Maximum log file size
  backup_count: 5            # Number of backup files
  
  # Component-specific logging
  components:
    llm_interface: "DEBUG"
    evaluation_engine: "INFO"
    controller: "INFO"
    diff_applier: "WARNING"
```

### Custom Log Formats

```yaml
logging:
  format: "[{timestamp}] {level} | {component} | {message}"
  timestamp_format: "%Y-%m-%d %H:%M:%S"
  
  # Structured logging for analysis
  structured: true
  output_format: "json"      # Options: text, json
```

## Progress Tracking

### Checkpoint-based Tracking

Monitor progress across checkpoints:

```bash
# View checkpoint history
alphaevolve checkpoints list --detailed

# Compare checkpoints
alphaevolve checkpoints compare \
  checkpoints/generation_50.json \
  checkpoints/generation_100.json
```

### Progress Reports

Generate detailed progress reports:

```bash
# Generate comprehensive report
alphaevolve analyze \
  --archive results/archive.json \
  --report progress_report.html \
  --include-plots
```

## Custom Monitoring

### Event Callbacks

Register custom callbacks for monitoring events:

```python
# custom_monitor.py
def on_generation_complete(generation, population, metrics):
    """Called after each generation completes."""
    print(f"Generation {generation}: Best fitness = {metrics['best_fitness']}")
    
    # Custom analysis
    if generation % 10 == 0:
        analyze_population_trends(population)
        save_generation_snapshot(generation, population)

def on_new_best_found(individual, generation):
    """Called when a new best individual is found."""
    print(f"New best found in generation {generation}!")
    save_best_individual(individual, generation)

def on_evolution_complete(final_population, archive):
    """Called when evolution completes."""
    generate_final_report(final_population, archive)
```

Register callbacks in your configuration:

```yaml
monitoring:
  callbacks:
    module: "custom_monitor"
    functions:
      - "on_generation_complete"
      - "on_new_best_found" 
      - "on_evolution_complete"
```

### Custom Metrics

Define custom metrics to track:

```python
# custom_metrics.py
def calculate_code_elegance(individual):
    """Measure code elegance."""
    lines_of_code = count_lines(individual.code)
    cyclomatic_complexity = calculate_complexity(individual.code)
    return 1.0 / (1.0 + lines_of_code * cyclomatic_complexity)

def measure_innovation(individual, population):
    """Measure how innovative an individual is."""
    similarities = [calculate_similarity(individual, other) 
                   for other in population if other != individual]
    return 1.0 - max(similarities) if similarities else 1.0
```

Configure custom metrics:

```yaml
monitoring:
  custom_metrics:
    - name: "code_elegance"
      function: "custom_metrics.calculate_code_elegance"
      display_name: "Code Elegance"
      
    - name: "innovation"
      function: "custom_metrics.measure_innovation"
      display_name: "Innovation Score"
      requires_population: true
```

## Performance Monitoring

### System Resource Monitoring

Track system resource usage:

```yaml
monitoring:
  system:
    enabled: true
    track_memory: true
    track_cpu: true
    track_disk: true
    
    # Alerts
    memory_alert_threshold: 0.8    # Alert at 80% memory usage
    cpu_alert_threshold: 0.9       # Alert at 90% CPU usage
```

### LLM Performance Monitoring

Monitor LLM service performance:

```yaml
monitoring:
  llm:
    track_latency: true
    track_token_usage: true
    track_cost: true
    
    # Cost tracking
    cost_per_1k_tokens:
      input: 0.01
      output: 0.03
    
    # Performance alerts
    latency_alert_threshold: 30    # Alert if response > 30s
    failure_rate_alert: 0.1        # Alert if failure rate > 10%
```

## Visualization

### Built-in Plots

AlphaEvolve generates several standard plots:

1. **Fitness Over Time**: Best and average fitness progression
2. **Population Diversity**: Diversity metrics over generations
3. **Behavioral Heatmap**: Distribution across behavioral dimensions
4. **LLM Performance**: Success rates and response times
5. **Archive Growth**: Archive utilization over time

### Custom Visualizations

Create custom plots with the monitoring API:

```python
# custom_plots.py
import matplotlib.pyplot as plt
from alphaevolve.monitoring import get_evolution_data

def plot_custom_metrics():
    """Generate custom visualization."""
    data = get_evolution_data()
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Plot 1: Fitness vs Complexity
    fitness_vals = [gen['best_fitness'] for gen in data]
    complexity_vals = [gen['avg_complexity'] for gen in data]
    
    ax1.scatter(complexity_vals, fitness_vals, alpha=0.7)
    ax1.set_xlabel('Average Complexity')
    ax1.set_ylabel('Best Fitness')
    ax1.set_title('Fitness vs Complexity Trade-off')
    
    # Plot 2: Innovation over time
    innovation_vals = [gen['innovation_score'] for gen in data]
    generations = list(range(len(innovation_vals)))
    
    ax2.plot(generations, innovation_vals, 'b-', linewidth=2)
    ax2.set_xlabel('Generation')
    ax2.set_ylabel('Innovation Score')
    ax2.set_title('Innovation Over Time')
    
    plt.tight_layout()
    plt.savefig('custom_analysis.png', dpi=300, bbox_inches='tight')
```

## Alerts and Notifications

### Email Notifications

Configure email alerts for important events:

```yaml
monitoring:
  notifications:
    email:
      enabled: true
      smtp_server: "smtp.gmail.com"
      smtp_port: 587
      username: "your_email@gmail.com"
      password_env: "EMAIL_PASSWORD"
      
      # Recipients
      recipients:
        - "researcher@university.edu"
        - "team@company.com"
      
      # Alert conditions
      alerts:
        - condition: "new_best_fitness"
          threshold: 0.9
          message: "New high-fitness individual found!"
          
        - condition: "stagnation"
          generations: 50
          message: "Evolution may have stagnated"
```

### Slack Integration

Send updates to Slack channels:

```yaml
monitoring:
  notifications:
    slack:
      enabled: true
      webhook_url_env: "SLACK_WEBHOOK_URL"
      channel: "#evolution-results"
      
      # Periodic updates
      update_interval: 100       # Every 100 generations
      include_plots: true
```

## Troubleshooting Monitoring

### Common Issues

#### High Memory Usage

Monitor and optimize memory usage:

```yaml
monitoring:
  memory_optimization:
    enable_gc_monitoring: true
    gc_frequency: 50           # Generations between garbage collection
    max_memory_per_process: "2GB"
    
    # Memory alerts
    alert_threshold: 0.8
    emergency_cleanup: true
```

#### Slow Dashboard Updates

Optimize web dashboard performance:

```yaml
monitoring:
  web:
    # Reduce update frequency
    update_frequency: 5
    
    # Limit data retention
    max_data_points: 500
    
    # Disable expensive features
    enable_code_viewer: false
    enable_realtime_plots: false
```

#### Log File Size Issues

Manage log file growth:

```yaml
logging:
  # Rotate logs more frequently
  max_size: "50MB"
  backup_count: 3
  
  # Reduce verbosity
  level: "INFO"
  components:
    llm_interface: "WARNING"
    evaluation_engine: "ERROR"
```

## Next Steps

- [Manage checkpoints and recovery](checkpoints.md)
- [Analyze evolution results](../examples/analysis-tutorial.md)
- [Configure advanced evolution parameters](configuration-reference.md)