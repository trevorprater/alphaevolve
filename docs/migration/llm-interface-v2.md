# LLM Interface v2 Migration Guide

This guide helps you migrate from the original LLM interface to the advanced v2 interface with support for multiple providers.

## Overview of Changes

### New Features

1. **Multiple LLM Providers**
   - Anthropic (Claude) with thinking parameter support
   - OpenAI (GPT-4)
   - Google Vertex AI (Gemini models)
   - Google Gemini API
   - Mock provider for testing

2. **Advanced Error Handling**
   - Circuit breaker pattern for provider failures
   - Exponential backoff with configurable retry strategies
   - Automatic fallback to alternative providers

3. **Performance Optimizations**
   - Token bucket rate limiting
   - Request batching support
   - Concurrent request handling
   - Response caching (configurable)

4. **Enhanced Response Format**
   - Detailed token usage tracking
   - Cost estimation
   - Latency measurements
   - Thinking content for supported models

## Migration Steps

### 1. Update Configuration

#### Old Configuration
```yaml
llm:
  default_provider: openai
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      model: gpt-4
      temperature: 0.2
      max_tokens: 2000
```

#### New Configuration
```yaml
llm:
  default_provider: anthropic  # Recommended: Use Anthropic as primary
  fallback_provider: openai
  
  providers:
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
      model: claude-3-sonnet-20240229
      temperature: 0.2
      max_tokens: 4000
      timeout_seconds: 60
      rate_limit_rpm: 60
      
    openai:
      api_key: ${OPENAI_API_KEY}
      model: gpt-4-turbo-preview
      temperature: 0.2
      max_tokens: 4000
      timeout_seconds: 60
      rate_limit_rpm: 60
      
    vertex_ai:
      api_key: ""  # Uses ADC
      model: gemini-1.5-pro
      temperature: 0.2
      max_tokens: 8000
      
    gemini:
      api_key: ${GOOGLE_API_KEY}
      model: gemini-pro
      temperature: 0.2
      max_tokens: 8000
```

### 2. Update Code Usage

#### Old Interface Usage
```python
from alpha_evolve.llm_interface import LLMInterface

# Initialize
llm = LLMInterface()

# Generate code
result = await llm.generate_code_modification(
    prompt="Optimize this function",
    llm_type="pro"  # or "flash"
)

# Result is a string
print(result)
```

#### New Interface Usage
```python
from alpha_evolve.llm_interface_v2 import LLMInterface

# Initialize
llm = LLMInterface()

# Generate code with automatic fallback
response = await llm.generate_code_modification(
    prompt="Optimize this function",
    provider="anthropic",  # Optional: specify provider
    use_thinking=True,     # Enable thinking for supported models
    thinking_budget=8192   # Thinking token budget
)

# Response is now an LLMResponse object
print(f"Content: {response.content}")
print(f"Provider: {response.provider}")
print(f"Tokens: {response.tokens_used}")
print(f"Cost: ${response.cost:.4f}")
print(f"Latency: {response.latency:.2f}s")

if response.thinking_content:
    print(f"Thinking: {response.thinking_content}")
```

### 3. Update Import Statements

```python
# Old
from alpha_evolve.llm_interface import LLMInterface, LLMResponse

# New
from alpha_evolve.llm_interface_v2 import (
    LLMInterface, 
    LLMResponse,
    ProviderConfig,
    RetryStrategy
)
```

### 4. Handle New Response Format

The new `LLMResponse` object provides more information:

```python
@dataclass
class LLMResponse:
    content: str                          # The generated content
    provider: str                         # Which provider was used
    model: str                           # Model name
    tokens_used: Optional[Dict[str, int]] # {input, output, total}
    cost: Optional[float]                # Estimated cost in USD
    latency: Optional[float]             # Response time in seconds
    thinking_content: Optional[str]      # Thinking process (if available)
    metadata: Dict[str, Any]             # Additional provider-specific data
```

### 5. Environment Variables

Set up environment variables for each provider:

```bash
# Anthropic
export ANTHROPIC_API_KEY="your-anthropic-key"

# OpenAI
export OPENAI_API_KEY="your-openai-key"

# Google Cloud (for Vertex AI)
export GOOGLE_CLOUD_PROJECT="your-project-id"
# Or use Application Default Credentials:
gcloud auth application-default login

# Google Gemini API
export GOOGLE_API_KEY="your-google-api-key"
```

## Feature Comparison

| Feature | v1 | v2 |
|---------|----|----|
| Providers | OpenAI, Anthropic, Mock | + Vertex AI, Gemini |
| Error Handling | Basic retry | Circuit breaker + exponential backoff |
| Rate Limiting | Simple | Token bucket algorithm |
| Response Format | String | Structured LLMResponse |
| Thinking Support | No | Yes (Anthropic) |
| Cost Tracking | No | Yes |
| Fallback | Manual | Automatic |
| Concurrent Requests | Limited | Full support |

## Advanced Features

### Using Thinking Parameter (Anthropic)

```python
# Enable extended thinking for complex tasks
response = await llm.generate_code_modification(
    prompt="Implement a complex algorithm",
    provider="anthropic",
    use_thinking=True,
    thinking_budget=16384  # More tokens for deeper thinking
)

# Access thinking process
if response.thinking_content:
    print("Claude's thought process:")
    print(response.thinking_content)
```

### Custom Retry Configuration

```python
from alpha_evolve.llm_interface_v2 import ProviderConfig, RetryStrategy

config = ProviderConfig(
    api_key="your-key",
    model="gpt-4",
    max_retries=5,
    retry_strategy=RetryStrategy.EXPONENTIAL,
    timeout=120
)
```

### Provider-Specific Features

```python
# Vertex AI with custom location
response = await llm.generate_code_modification(
    prompt="Generate code",
    provider="vertex_ai",
    location="europe-west4",  # Custom region
    project_id="my-project"
)

# OpenAI with custom parameters
response = await llm.generate_code_modification(
    prompt="Generate code",
    provider="openai",
    model="gpt-4-1106-preview",  # Latest model
    response_format={"type": "json_object"}  # JSON mode
)
```

## Backward Compatibility

To maintain backward compatibility during migration:

1. The `llm_type` parameter is still supported but deprecated
2. String results can be extracted using `response.content`
3. The mock provider maintains the same behavior

```python
# This still works but is deprecated
result = await llm.generate_code_modification(
    prompt="Test",
    llm_type="pro"  # Maps to appropriate model
)

# Access content for backward compatibility
content = result.content if hasattr(result, 'content') else result
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Install required dependencies
   pip install google-cloud-aiplatform  # For Vertex AI
   pip install google-generativeai      # For Gemini API
   ```

2. **Authentication Errors**
   - Ensure all API keys are set in environment variables
   - For Vertex AI, ensure Google Cloud SDK is configured
   - Check API key permissions and quotas

3. **Rate Limiting**
   - The new interface automatically handles rate limits
   - Adjust `rate_limit_rpm` in configuration if needed

4. **Circuit Breaker Open**
   - Wait for recovery timeout (default 60s)
   - Check provider status and API health
   - Use fallback providers

## Best Practices

1. **Use Anthropic as Primary Provider**
   - Supports advanced thinking parameter
   - Generally more capable for code generation

2. **Configure Fallback Chain**
   - Set up multiple providers for reliability
   - Order by preference and capability

3. **Monitor Costs**
   - Use `response.cost` to track spending
   - Set up alerts for budget limits

4. **Leverage Provider Strengths**
   - Anthropic: Complex reasoning with thinking
   - OpenAI: Fast responses, wide model selection
   - Vertex AI/Gemini: Large context windows

## Next Steps

1. Update your configuration file
2. Set up environment variables
3. Update import statements
4. Test with different providers
5. Monitor performance and costs
6. Optimize provider selection based on task requirements