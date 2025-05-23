# LLM Provider Setup

This guide explains how to configure API keys and credentials for each LLM provider.

## OpenAI

### API Key Setup
1. Create an account at [platform.openai.com](https://platform.openai.com)
2. Generate an API key from the API keys section
3. Set the environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```

### Supported Models
- **o4**: Most capable reasoning model
- **o4-mini**: Cost-effective reasoning model
- **o3**: Advanced reasoning model
- **o1**: Production reasoning model
- **o1-mini**: Fast reasoning model
- **gpt-4**: Standard GPT-4
- **gpt-4o**: Optimized GPT-4

## Anthropic

### API Key Setup
1. Create an account at [console.anthropic.com](https://console.anthropic.com)
2. Generate an API key from the API keys section
3. Set the environment variable:
   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

### Supported Models
- **claude-opus-4**: Most capable model with thinking support
- **claude-sonnet-4**: Balanced model with thinking support
- **claude-3-5-sonnet-v2**: Fast, efficient model

### Thinking Mode
Claude 4 models support "thinking mode" for enhanced reasoning:
```yaml
anthropic:
  use_thinking: true
  thinking_budget: 8192  # Token budget for thinking
```

## Google Gemini

### API Key Setup (Gemini API)
1. Get API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set the environment variable:
   ```bash
   export GOOGLE_API_KEY="..."
   ```

### Supported Models
- **gemini-2.5-flash**: Fast, efficient model
- **gemini-2.5-pro**: Advanced capabilities
- **gemini-2.0-flash**: Latest flash model

## Vertex AI (Google Cloud)

### Setup
1. Create a Google Cloud project
2. Enable the Vertex AI API
3. Set up Application Default Credentials:
   ```bash
   gcloud auth application-default login
   ```
4. Set environment variables:
   ```bash
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   export GOOGLE_CLOUD_LOCATION="us-central1"  # Optional
   ```

### Supported Models
Same as Gemini API models, but accessed through Vertex AI.

## Configuration Example

```yaml
llm:
  default_provider: "anthropic"
  fallback_provider: "gemini"
  
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      model: "o1-mini"
      
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
      model: "claude-3-5-sonnet-v2"
      use_thinking: true
      
    gemini:
      api_key: ${GOOGLE_API_KEY}
      model: "gemini-2.5-flash"
      
    vertex_ai:
      project: ${GOOGLE_CLOUD_PROJECT}
      location: "us-central1"
      model: "gemini-2.5-pro"
```

## Installing Provider SDKs

Each provider requires its SDK to be installed:

```bash
# For OpenAI
uv pip install openai

# For Anthropic
uv pip install anthropic

# For Google (both Gemini and Vertex AI)
uv pip install google-genai

# Or install all at once
uv pip install openai anthropic google-genai
```

## Testing Your Setup

After configuration, test with:

```bash
alphaevolve test-llm --provider openai
alphaevolve test-llm --provider anthropic
alphaevolve test-llm --provider gemini
alphaevolve test-llm --provider vertex_ai
```