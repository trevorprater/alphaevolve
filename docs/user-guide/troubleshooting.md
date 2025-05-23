# Troubleshooting Guide

This guide helps you resolve common issues with AlphaEvolve.

## Common Issues

### Evolution Stagnates

If your evolution stops improving:

1. **Increase diversity**: Adjust behavioral diversity weight in configuration
2. **Increase mutation rate**: Try higher temperature or mutation rate
3. **Check evaluation function**: Ensure it provides meaningful gradients

See [Configuration Reference](configuration-reference.md#evolution-algorithm-configuration) for details.

### LLM Errors

Common LLM-related issues:

1. **API Key Issues**: Ensure environment variables are set correctly
2. **Rate Limits**: Reduce parallel LLM calls or add delays
3. **Timeouts**: Increase timeout values in configuration

See [LLM Configuration](configuration-reference.md#llm-configuration) for solutions.

### Memory Issues

If you encounter out-of-memory errors:

1. **Reduce parallelism**: Lower `parallel_evaluations` setting
2. **Enable garbage collection**: Set aggressive GC in configuration
3. **Limit population size**: Use smaller populations

See [Performance Configuration](configuration-reference.md#performance-configuration) for details.

### Checkpoint Errors

For checkpoint-related issues:

1. **Verify disk space**: Ensure sufficient storage available
2. **Check permissions**: Verify write permissions to checkpoint directory
3. **Validate checkpoints**: Use `alphaevolve checkpoints verify`

See [Checkpoints Guide](checkpoints.md) for recovery procedures.

## Getting Help

If you can't resolve an issue:

1. Check the [FAQ section](#frequently-asked-questions)
2. Search existing [GitHub issues](https://github.com/yourusername/alphaevolve/issues)
3. Create a new issue with:
   - AlphaEvolve version
   - Configuration file
   - Error messages
   - Steps to reproduce

## Frequently Asked Questions

**Q: Why is evolution slow?**
A: Check your LLM provider, parallel settings, and evaluation complexity.

**Q: Can I resume a failed experiment?**
A: Yes, use checkpoints. See [Checkpoints Guide](checkpoints.md).

**Q: How do I optimize for multiple objectives?**
A: Use behavioral dimensions and multi-objective evaluation. See [Evaluation Functions](evaluation-functions.md).