# Checkpoints and Recovery

AlphaEvolve's checkpoint system enables you to save evolution state, resume interrupted experiments, and analyze progress over time.

## Automatic Checkpointing

### Enable Automatic Saves

Configure automatic checkpoint creation:

```yaml
# evolution_config.yaml
checkpointing:
  enabled: true
  interval: 10                # Save every 10 generations
  directory: "checkpoints"    # Checkpoint directory
  max_checkpoints: 20         # Keep last 20 checkpoints
  
  # Compression
  compress: true
  compression_level: 6        # 1-9, higher = smaller files
  
  # Backup
  backup_to_cloud: false      # Optional cloud backup
  cloud_provider: "s3"       # s3, gcs, azure
```

### Checkpoint Frequency

Choose appropriate checkpoint intervals:

```yaml
checkpointing:
  # For short experiments (< 100 generations)
  interval: 5
  
  # For medium experiments (100-500 generations)  
  interval: 25
  
  # For long experiments (> 500 generations)
  interval: 50
  
  # For expensive experiments (slow LLM calls)
  interval: 1                 # Checkpoint every generation
```

## Running with Checkpoints

### Start with Checkpointing

```bash
# Enable checkpointing from the start
alphaevolve evolve \
  --config evolution_config.yaml \
  --checkpoint-interval 10 \
  --checkpoint-dir ./checkpoints
```

### Resume from Checkpoint

```bash
# Resume from latest checkpoint
alphaevolve evolve --resume checkpoints/latest.json

# Resume from specific checkpoint
alphaevolve evolve --resume checkpoints/generation_150.json

# Resume with different configuration
alphaevolve evolve \
  --resume checkpoints/generation_150.json \
  --config new_config.yaml \
  --max-generations 300
```

## Checkpoint Management

### List Checkpoints

```bash
# List all checkpoints
alphaevolve checkpoints list

# Detailed checkpoint information
alphaevolve checkpoints list --detailed

# Filter by date or generation
alphaevolve checkpoints list --after "2024-01-01" --before "2024-02-01"
alphaevolve checkpoints list --min-generation 50 --max-generation 150
```

Example output:
```
Checkpoints in ./checkpoints:
├─ generation_025.json  (Jan 15 14:30)  25 gens, 156 archive, best: 0.823
├─ generation_050.json  (Jan 15 15:45)  50 gens, 234 archive, best: 0.856  
├─ generation_075.json  (Jan 15 17:12)  75 gens, 287 archive, best: 0.871
├─ generation_100.json  (Jan 15 18:34) 100 gens, 324 archive, best: 0.889
└─ latest.json -> generation_100.json
```

### Compare Checkpoints

```bash
# Compare two checkpoints
alphaevolve checkpoints compare \
  checkpoints/generation_050.json \
  checkpoints/generation_100.json

# Compare with current state
alphaevolve checkpoints compare \
  checkpoints/generation_075.json \
  --current
```

### Cleanup Old Checkpoints

```bash
# Remove checkpoints older than 30 days
alphaevolve checkpoints cleanup --older-than 30d

# Keep only the last 10 checkpoints
alphaevolve checkpoints cleanup --keep-last 10

# Remove checkpoints with fitness below threshold
alphaevolve checkpoints cleanup --min-fitness 0.5
```

## Manual Checkpoint Operations

### Create Manual Checkpoint

```bash
# Create checkpoint of current state
alphaevolve checkpoints create --output manual_checkpoint.json

# Create checkpoint with metadata
alphaevolve checkpoints create \
  --output experiment_milestone.json \
  --label "Before algorithm change" \
  --notes "Baseline before implementing new mutation strategy"
```

### Restore from Checkpoint

```bash
# Restore evolution state (overwrites current state)
alphaevolve checkpoints restore checkpoints/generation_075.json

# Restore with backup of current state
alphaevolve checkpoints restore \
  checkpoints/generation_075.json \
  --backup-current current_backup.json
```

### Extract Information

```bash
# Extract best programs from checkpoint
alphaevolve checkpoints extract \
  checkpoints/generation_100.json \
  --best 5 \
  --output best_programs.json

# Extract archive data
alphaevolve checkpoints extract \
  checkpoints/generation_100.json \
  --archive \
  --output archive_data.json

# Extract population
alphaevolve checkpoints extract \
  checkpoints/generation_100.json \
  --population \
  --format python \
  --output population.py
```

## Checkpoint Contents

### Standard Checkpoint Structure

```json
{
  "metadata": {
    "version": "1.0.0",
    "timestamp": "2024-01-15T18:34:22Z",
    "generation": 100,
    "experiment_id": "exp_2024_0115_001",
    "label": "Checkpoint at generation 100",
    "notes": "Automatic checkpoint"
  },
  
  "configuration": {
    "evolution_config": { /* Original evolution config */ },
    "runtime_config": { /* Runtime parameters */ }
  },
  
  "population": [
    {
      "id": "prog_001",
      "code": "def optimized_function(x):\n    return x ** 2 + 1",
      "fitness": 0.889,
      "behavior": [0.67, 23.4, 0.45],
      "generation_created": 87,
      "parent_ids": ["prog_045", "prog_122"],
      "mutation_history": [ /* Mutation log */ ]
    }
    /* ... more individuals ... */
  ],
  
  "archive": {
    "size": 324,
    "individuals": [ /* Archive contents */ ],
    "behavioral_dimensions": 3,
    "dimension_ranges": [ /* Dimension info */ ]
  },
  
  "statistics": {
    "best_fitness": 0.889,
    "average_fitness": 0.634,
    "population_diversity": 0.723,
    "archive_utilization": 0.324,
    "generation_times": [ /* Timing data */ ],
    "llm_statistics": { /* LLM performance */ }
  },
  
  "evolution_history": {
    "fitness_history": [ /* Fitness over time */ ],
    "diversity_history": [ /* Diversity over time */ ],
    "milestone_generations": [25, 50, 75, 100]
  }
}
```

### Custom Checkpoint Data

Add custom data to checkpoints:

```python
# custom_checkpointing.py
def add_custom_checkpoint_data(checkpoint_data, population, archive):
    """Add custom data to checkpoint."""
    
    # Add algorithm-specific metrics
    checkpoint_data['custom_metrics'] = {
        'code_complexity_trend': calculate_complexity_trend(population),
        'innovation_score': measure_population_innovation(population),
        'convergence_rate': estimate_convergence_rate(population)
    }
    
    # Add experiment-specific data
    checkpoint_data['experiment_data'] = {
        'parameter_sweep_progress': get_parameter_progress(),
        'hypothesis_testing_results': get_hypothesis_results(),
        'research_notes': get_current_research_notes()
    }
    
    return checkpoint_data
```

Configure custom checkpointing:

```yaml
checkpointing:
  custom_data_handler: "custom_checkpointing.add_custom_checkpoint_data"
  include_full_history: true
  include_code_diffs: true
```

## Distributed Checkpointing

### Multi-Node Experiments

For distributed evolution across multiple machines:

```yaml
checkpointing:
  distributed:
    enabled: true
    coordinator_node: true      # This node manages checkpoints
    sync_interval: 5           # Sync every 5 generations
    
    # Shared storage
    shared_directory: "/shared/checkpoints"
    backup_nodes: ["node2", "node3"]
    
    # Consistency
    require_consensus: true     # All nodes must agree on checkpoint
    max_sync_retries: 3
```

### Cloud Synchronization

Automatically sync checkpoints to cloud storage:

```yaml
checkpointing:
  cloud_sync:
    enabled: true
    provider: "s3"             # s3, gcs, azure, dropbox
    bucket: "my-evolution-checkpoints"
    path_prefix: "experiments/alphaevolve"
    
    # Sync settings
    sync_on_create: true       # Upload immediately after creation
    sync_interval: 300         # Also sync every 5 minutes
    encryption: true           # Encrypt before upload
    
    # Credentials
    credentials_env: "AWS_CREDENTIALS"
```

## Recovery Strategies

### Automatic Recovery

Configure automatic recovery from failures:

```yaml
recovery:
  auto_recovery: true
  max_recovery_attempts: 3
  
  # Recovery strategies (in order of preference)
  strategies:
    - "resume_from_latest_checkpoint"
    - "resume_from_previous_generation"
    - "restart_from_last_stable_generation"
    - "restart_with_population_backup"
  
  # Failure detection
  detect_corruption: true
  verify_checkpoints: true
  health_check_interval: 60   # Seconds
```

### Manual Recovery

#### Corrupted Checkpoint Recovery

```bash
# Verify checkpoint integrity
alphaevolve checkpoints verify generation_100.json

# Attempt to repair corrupted checkpoint
alphaevolve checkpoints repair \
  generation_100.json \
  --output generation_100_repaired.json

# Use backup checkpoint
alphaevolve evolve --resume generation_075.json
```

#### Partial Data Recovery

```bash
# Extract salvageable data from corrupted checkpoint
alphaevolve checkpoints salvage \
  corrupted_checkpoint.json \
  --extract-population \
  --extract-archive \
  --output salvaged_data/

# Resume with salvaged population
alphaevolve evolve \
  --config evolution_config.yaml \
  --import-population salvaged_data/population.json \
  --import-archive salvaged_data/archive.json
```

## Checkpoint Analysis

### Progress Analysis

Analyze evolution progress across checkpoints:

```bash
# Generate progress report
alphaevolve checkpoints analyze \
  --directory checkpoints/ \
  --report progress_analysis.html \
  --include-plots

# Compare multiple experiments
alphaevolve checkpoints analyze \
  --experiments exp1/checkpoints exp2/checkpoints exp3/checkpoints \
  --comparative-report comparison.html
```

### Statistical Analysis

```python
# analyze_checkpoints.py
from alphaevolve.analysis import CheckpointAnalyzer

def analyze_experiment_checkpoints():
    """Analyze evolution progress from checkpoints."""
    
    analyzer = CheckpointAnalyzer("checkpoints/")
    
    # Load all checkpoints
    checkpoints = analyzer.load_all_checkpoints()
    
    # Fitness progression analysis
    fitness_trend = analyzer.analyze_fitness_progression(checkpoints)
    print(f"Fitness improvement rate: {fitness_trend['improvement_rate']:.4f}")
    print(f"Convergence detected: {fitness_trend['converged']}")
    
    # Diversity analysis
    diversity_trend = analyzer.analyze_diversity(checkpoints)
    print(f"Diversity maintained: {diversity_trend['diversity_maintained']}")
    
    # Archive growth analysis
    archive_analysis = analyzer.analyze_archive_growth(checkpoints)
    print(f"Archive utilization: {archive_analysis['final_utilization']:.2%}")
    
    # Generate plots
    analyzer.plot_fitness_over_time()
    analyzer.plot_diversity_heatmap()
    analyzer.plot_archive_growth()
    
    return analyzer.generate_summary_report()
```

## Best Practices

### Checkpoint Strategy

1. **Frequency**: Balance between safety and storage space
2. **Retention**: Keep milestone checkpoints longer than regular ones
3. **Verification**: Regularly verify checkpoint integrity
4. **Documentation**: Add meaningful labels and notes
5. **Backup**: Use multiple storage locations for important experiments

### Storage Management

```yaml
checkpointing:
  storage:
    # Compression settings
    compress: true
    compression_level: 6
    
    # Retention policy
    retention:
      keep_all_until_generations: 100
      keep_milestones: [25, 50, 100, 200, 500]
      keep_last_n: 10
      keep_best_fitness: true
      
    # Cleanup automation
    auto_cleanup: true
    cleanup_interval: "daily"
    max_storage_size: "10GB"
```

### Security Considerations

```yaml
checkpointing:
  security:
    encrypt_checkpoints: true
    encryption_key_env: "CHECKPOINT_ENCRYPTION_KEY"
    verify_integrity: true
    
    # Access control
    file_permissions: "600"    # Read/write for owner only
    backup_permissions: "400"  # Read-only backups
```

## Next Steps

- [Analyze evolution results](../examples/analysis-tutorial.md)
- [Configure advanced monitoring](monitoring.md)
- [Set up distributed evolution](../advanced/distributed-evolution.md)