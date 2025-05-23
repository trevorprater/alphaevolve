"""
Interface for interacting with Large Language Models for code generation.

This module provides a unified interface for multiple LLM providers with modern
SDK support, including advanced features like thinking modes and structured outputs.
"""
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Union
import os
from enum import Enum
from contextlib import asynccontextmanager

# Provider SDKs
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import google.genai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from alpha_evolve.config import get_config


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    latency: Optional[float] = None
    thinking_content: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: Optional[str] = None, **config):
        """
        Initialize the LLM provider.
        
        Args:
            api_key: API key for the provider (optional for some providers)
            **config: Provider-specific configuration
        """
        self.api_key = api_key
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._client = None
        
    @abstractmethod
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """
        Generate code based on prompt.
        
        Args:
            prompt: The input prompt for code generation
            **kwargs: Provider-specific parameters
            
        Returns:
            LLMResponse with generated code or diff
        """
        pass
        
    @abstractmethod
    async def critique_code(self, code: str, criteria: str) -> LLMResponse:
        """
        Provide critique of code based on criteria.
        
        Args:
            code: The code to critique
            criteria: Criteria for evaluation
            
        Returns:
            LLMResponse with structured critique
        """
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if hasattr(self._client, 'close'):
            await self._client.close()


class OpenAIProvider(LLMProvider):
    """OpenAI-specific implementation supporting o4, o3, o1 models."""
    
    MODELS = {
        'o4': {'name': 'o4', 'cost_per_1k_input': 0.150, 'cost_per_1k_output': 0.600},
        'o4-mini': {'name': 'o4-mini', 'cost_per_1k_input': 0.015, 'cost_per_1k_output': 0.060},
        'o3': {'name': 'o3', 'cost_per_1k_input': 0.100, 'cost_per_1k_output': 0.400},
        'o1': {'name': 'o1', 'cost_per_1k_input': 0.015, 'cost_per_1k_output': 0.060},
        'o1-mini': {'name': 'o1-mini', 'cost_per_1k_input': 0.003, 'cost_per_1k_output': 0.012},
        'gpt-4': {'name': 'gpt-4', 'cost_per_1k_input': 0.030, 'cost_per_1k_output': 0.060},
        'gpt-4o': {'name': 'gpt-4o', 'cost_per_1k_input': 0.005, 'cost_per_1k_output': 0.015},
    }
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        if not HAS_OPENAI:
            raise ImportError("openai package not installed. Install with: pip install openai")
            
        self.model = config.get('model', 'o1-mini')
        self.temperature = config.get('temperature', 0.2)
        self.max_tokens = config.get('max_tokens', 2000)
        
        # Initialize OpenAI client
        self._client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=config.get('base_url'),
            timeout=config.get('timeout_seconds', 30),
            max_retries=config.get('max_retries', 2)
        )
    
    @property
    def name(self) -> str:
        return "openai"
        
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate code using OpenAI API."""
        start_time = time.time()
        
        model = kwargs.get('model', self.model)
        model_info = self.MODELS.get(model, self.MODELS['o1-mini'])
        
        try:
            # Handle reasoning models (o1, o3) differently
            if model in ['o1', 'o1-mini', 'o3', 'o3-mini', 'o4', 'o4-mini']:
                # Reasoning models don't support system messages or temperature
                response = await self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            'role': 'user',
                            'content': f"You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.\n\n{prompt}"
                        }
                    ],
                    max_completion_tokens=kwargs.get('max_tokens', self.max_tokens),
                    temperature=None,  # Not supported for reasoning models
                    reasoning_effort=kwargs.get('reasoning_effort', 'medium')  # For o1 models
                )
            else:
                # Standard models (gpt-4, gpt-4o)
                response = await self._client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            'role': 'system',
                            'content': 'You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.'
                        },
                        {
                            'role': 'user', 
                            'content': prompt
                        }
                    ],
                    temperature=kwargs.get('temperature', self.temperature),
                    max_tokens=kwargs.get('max_tokens', self.max_tokens)
                )
            
            content = response.choices[0].message.content
            usage = response.usage
            
            # Calculate cost
            input_cost = (usage.prompt_tokens / 1000) * model_info['cost_per_1k_input']
            output_cost = (usage.completion_tokens / 1000) * model_info['cost_per_1k_output']
            total_cost = input_cost + output_cost
            
            latency = time.time() - start_time
            self.logger.info(f"OpenAI request completed in {latency:.2f}s using {model}")
            
            return LLMResponse(
                content=content,
                provider=self.name,
                model=model,
                tokens_used=usage.total_tokens,
                cost=total_cost,
                latency=latency,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens
                }
            )
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API error: {str(e)}")
                
    async def critique_code(self, code: str, criteria: str) -> LLMResponse:
        """Provide code critique using OpenAI."""
        prompt = f"""
Please critique the following code based on these criteria: {criteria}

Code to analyze:
```python
{code}
```

Provide a structured critique covering:
1. Correctness
2. Performance
3. Readability
4. Best practices
5. Potential issues

Format your response as JSON with scores (1-10) and explanations.
"""
        return await self.generate_code(prompt)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude-specific implementation with thinking support."""
    
    MODELS = {
        'claude-opus-4': {'name': 'claude-opus-4', 'cost_per_1k_input': 0.015, 'cost_per_1k_output': 0.075},
        'claude-sonnet-4': {'name': 'claude-sonnet-4', 'cost_per_1k_input': 0.003, 'cost_per_1k_output': 0.015},
        'claude-3-5-sonnet-v2': {'name': 'claude-3-5-sonnet-20241022', 'cost_per_1k_input': 0.003, 'cost_per_1k_output': 0.015},
    }
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package not installed. Install with: pip install anthropic")
            
        self.model = config.get('model', 'claude-3-5-sonnet-v2')
        self.max_tokens = config.get('max_tokens', 2000)
        self.temperature = config.get('temperature', 0.2)
        self.use_thinking = config.get('use_thinking', True)
        
        # Initialize Anthropic client
        self._client = anthropic.AsyncAnthropic(
            api_key=self.api_key,
            base_url=config.get('base_url'),
            timeout=config.get('timeout_seconds', 30),
            max_retries=config.get('max_retries', 2)
        )
    
    @property
    def name(self) -> str:
        return "anthropic"
        
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate code using Anthropic Claude API."""
        start_time = time.time()
        
        model = kwargs.get('model', self.model)
        model_name = self.MODELS.get(model, self.MODELS['claude-3-5-sonnet-v2'])['name']
        model_info = self.MODELS.get(model, self.MODELS['claude-3-5-sonnet-v2'])
        
        try:
            # Prepare messages
            messages = [
                {
                    'role': 'user',
                    'content': f"You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.\n\n{prompt}"
                }
            ]
            
            # Create request with optional thinking
            request_params = {
                'model': model_name,
                'max_tokens': kwargs.get('max_tokens', self.max_tokens),
                'messages': messages,
                'temperature': kwargs.get('temperature', self.temperature)
            }
            
            # Add thinking configuration for Claude 4 models
            if self.use_thinking and model in ['claude-opus-4', 'claude-sonnet-4']:
                request_params['thinking'] = {
                    'enabled': True,
                    'budget_tokens': kwargs.get('thinking_budget', 8192)
                }
            
            response = await self._client.messages.create(**request_params)
            
            # Extract content and thinking
            content = response.content[0].text if response.content else ""
            thinking_content = None
            
            # Check for thinking blocks in Claude 4 responses
            if hasattr(response, 'content') and len(response.content) > 1:
                for block in response.content:
                    if hasattr(block, 'type') and block.type == 'thinking':
                        thinking_content = block.thinking
                        break
            
            # Calculate cost
            usage = response.usage
            input_cost = (usage.input_tokens / 1000) * model_info['cost_per_1k_input']
            output_cost = (usage.output_tokens / 1000) * model_info['cost_per_1k_output']
            total_cost = input_cost + output_cost
            
            latency = time.time() - start_time
            self.logger.info(f"Anthropic request completed in {latency:.2f}s using {model_name}")
            
            return LLMResponse(
                content=content,
                provider=self.name,
                model=model,
                tokens_used=usage.input_tokens + usage.output_tokens,
                cost=total_cost,
                latency=latency,
                thinking_content=thinking_content,
                metadata={
                    'stop_reason': response.stop_reason,
                    'input_tokens': usage.input_tokens,
                    'output_tokens': usage.output_tokens
                }
            )
            
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            raise RuntimeError(f"Anthropic API error: {str(e)}")
                
    async def critique_code(self, code: str, criteria: str) -> LLMResponse:
        """Provide code critique using Claude."""
        prompt = f"""
Please critique the following code based on these criteria: {criteria}

Code to analyze:
```python
{code}
```

Provide a structured critique covering:
1. Correctness
2. Performance  
3. Readability
4. Best practices
5. Potential issues

Format your response as JSON with scores (1-10) and explanations.
"""
        return await self.generate_code(prompt)


class GeminiProvider(LLMProvider):
    """Google Gemini implementation using python-genai."""
    
    MODELS = {
        'gemini-2.5-flash': {'name': 'gemini-2.5-flash', 'cost_per_1k_input': 0.00025, 'cost_per_1k_output': 0.001},
        'gemini-2.5-pro': {'name': 'gemini-2.5-pro', 'cost_per_1k_input': 0.00125, 'cost_per_1k_output': 0.005},
        'gemini-2.0-flash': {'name': 'gemini-2.0-flash', 'cost_per_1k_input': 0.00025, 'cost_per_1k_output': 0.001},
    }
    
    def __init__(self, api_key: Optional[str] = None, **config):
        super().__init__(api_key, **config)
        if not HAS_GENAI:
            raise ImportError("google-genai package not installed. Install with: pip install google-genai")
            
        self.model = config.get('model', 'gemini-2.5-flash')
        self.temperature = config.get('temperature', 0.2)
        self.max_tokens = config.get('max_tokens', 2000)
        self.use_vertex = config.get('vertex_ai', False)
        
        # Initialize Gemini client
        if self.use_vertex:
            # Vertex AI mode
            self._client = genai.Client(
                vertexai=True,
                project=config.get('project'),
                location=config.get('location', 'us-central1'),
                credentials=config.get('credentials')
            )
        else:
            # Gemini API mode (requires API key)
            if not api_key:
                raise ValueError("API key required for Gemini API mode")
            self._client = genai.Client(api_key=api_key)
    
    @property
    def name(self) -> str:
        return "vertex_ai" if self.use_vertex else "gemini"
        
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate code using Gemini API."""
        start_time = time.time()
        
        model = kwargs.get('model', self.model)
        model_info = self.MODELS.get(model, self.MODELS['gemini-2.5-flash'])
        
        try:
            # Create model instance
            model_instance = self._client.models[model]
            
            # Prepare generation config
            generation_config = {
                'temperature': kwargs.get('temperature', self.temperature),
                'max_output_tokens': kwargs.get('max_tokens', self.max_tokens),
                'candidate_count': 1
            }
            
            # Generate response
            response = await model_instance.generate_content_async(
                f"You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.\n\n{prompt}",
                generation_config=generation_config
            )
            
            # Extract content
            content = response.text
            
            # Get token counts if available
            tokens_used = None
            if hasattr(response, 'usage_metadata'):
                tokens_used = response.usage_metadata.total_token_count
                input_tokens = response.usage_metadata.prompt_token_count
                output_tokens = response.usage_metadata.candidates_token_count
                
                # Calculate cost
                input_cost = (input_tokens / 1000) * model_info['cost_per_1k_input']
                output_cost = (output_tokens / 1000) * model_info['cost_per_1k_output']
                total_cost = input_cost + output_cost
            else:
                total_cost = None
                input_tokens = None
                output_tokens = None
            
            latency = time.time() - start_time
            self.logger.info(f"Gemini request completed in {latency:.2f}s using {model}")
            
            return LLMResponse(
                content=content,
                provider=self.name,
                model=model,
                tokens_used=tokens_used,
                cost=total_cost,
                latency=latency,
                metadata={
                    'finish_reason': response.candidates[0].finish_reason.name if response.candidates else None,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens
                }
            )
            
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            raise RuntimeError(f"Gemini API error: {str(e)}")
            
    async def critique_code(self, code: str, criteria: str) -> LLMResponse:
        """Provide code critique using Gemini."""
        prompt = f"""
Please critique the following code based on these criteria: {criteria}

Code to analyze:
```python
{code}
```

Provide a structured critique covering:
1. Correctness
2. Performance
3. Readability
4. Best practices
5. Potential issues

Format your response as JSON with scores (1-10) and explanations.
"""
        return await self.generate_code(prompt)


class MockProvider(LLMProvider):
    """Mock provider for testing."""
    
    def __init__(self, api_key: str = "mock", **config):
        super().__init__(api_key, **config)
        self.response_type = config.get('response_type', 'flash')
        self.model = config.get('model', 'mock-model')
        
    @property
    def name(self) -> str:
        return "mock"
        
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate mock code response."""
        start_time = time.time()
        await asyncio.sleep(0.1)  # Simulate latency
        
        # Check for llm_type in kwargs for backward compatibility
        response_type = kwargs.get('llm_type', self.response_type)
        
        if response_type == "flash":
            content = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 3  # Mock LLM modified logic\n>>>>>>>> REPLACE"
        elif response_type == "pro":
            content = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 5  # Pro model enhanced logic\n>>>>>>>> REPLACE"
        else:
            content = "<<<<<<<< SEARCH\noriginal_code\n========\nmodified_code\n>>>>>>>> REPLACE"
            
        latency = time.time() - start_time
        
        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            tokens_used=100,  # Mock token count
            cost=0.001,  # Mock cost
            latency=latency,
            metadata={'mock': True, 'response_type': response_type}
        )
            
    async def critique_code(self, code: str, criteria: str) -> LLMResponse:
        """Provide mock critique."""
        start_time = time.time()
        await asyncio.sleep(0.1)
        
        content = '{"correctness": 8, "performance": 7, "readability": 9, "issues": "Minor optimization possible"}'
        latency = time.time() - start_time
        
        return LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            tokens_used=50,
            cost=0.0005,
            latency=latency,
            metadata={'mock': True}
        )


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = []
        
    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        now = time.time()
        # Remove calls older than 1 minute
        self.calls = [call_time for call_time in self.calls if now - call_time < 60]
        
        if len(self.calls) >= self.calls_per_minute:
            sleep_time = 60 - (now - self.calls[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                
        self.calls.append(now)


class LLMInterface:
    """
    Main interface for LLM communication with multiple providers.
    
    This class manages multiple LLM providers with automatic fallback,
    rate limiting, and unified response handling.
    """
    
    def __init__(self):
        """Initialize the LLM interface."""
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider = None
        self.fallback_provider = None
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize providers from configuration
        self._setup_providers()
        
    def _setup_providers(self):
        """Setup providers from configuration."""
        config = get_config()
        
        # Provider initialization mapping
        provider_classes = {
            'openai': OpenAIProvider,
            'anthropic': AnthropicProvider,
            'gemini': GeminiProvider,
            'vertex_ai': GeminiProvider,
            'mock': MockProvider
        }
        
        # Setup providers from configuration
        for name, provider_config in config.llm.providers.items():
            try:
                provider_class = provider_classes.get(name)
                if not provider_class:
                    self.logger.warning(f"Unknown provider type: {name}")
                    continue
                    
                # Extract provider configuration
                config_dict = provider_config.model_dump() if hasattr(provider_config, 'model_dump') else dict(provider_config)
                
                # Special handling for Vertex AI
                if name == 'vertex_ai':
                    config_dict['vertex_ai'] = True
                    provider_class = GeminiProvider
                
                # Skip providers without API keys (except mock and vertex_ai)
                if name not in ['mock', 'vertex_ai'] and not config_dict.get('api_key'):
                    self.logger.info(f"Skipping {name} provider: no API key configured")
                    continue
                    
                # Create provider instance
                provider = provider_class(**config_dict)
                
                # Determine if this is the default or fallback provider
                is_default = (name == config.llm.default_provider)
                is_fallback = (name == config.llm.fallback_provider)
                
                self.register_provider(name, provider, default=is_default, fallback=is_fallback)
                    
            except Exception as e:
                self.logger.error(f"Failed to setup provider {name}: {e}")
        
        # Fallback to environment variables if no providers configured
        if not self.providers:
            self._setup_providers_from_env()
            
        # Always register mock provider if not already registered
        if 'mock' not in self.providers:
            mock_config = config.llm.providers.get('mock', {})
            config_dict = mock_config.model_dump() if hasattr(mock_config, 'model_dump') else dict(mock_config)
            mock_provider = MockProvider(**config_dict)
            is_default = (config.llm.default_provider == 'mock' or not self.providers)
            self.register_provider('mock', mock_provider, default=is_default)
        
    def _setup_providers_from_env(self):
        """Setup providers from environment variables (fallback)."""
        # OpenAI setup
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key and HAS_OPENAI:
            try:
                self.register_provider(
                    'openai', 
                    OpenAIProvider(api_key=openai_key, model='o1-mini'),
                    default=True
                )
            except Exception as e:
                self.logger.error(f"Failed to setup OpenAI from env: {e}")
            
        # Anthropic setup  
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key and HAS_ANTHROPIC:
            try:
                self.register_provider(
                    'anthropic',
                    AnthropicProvider(api_key=anthropic_key, model='claude-3-5-sonnet-v2'),
                    default=not self.default_provider  # Use as default if no OpenAI
                )
            except Exception as e:
                self.logger.error(f"Failed to setup Anthropic from env: {e}")
                
        # Gemini setup
        google_key = os.getenv('GOOGLE_API_KEY')
        if google_key and HAS_GENAI:
            try:
                self.register_provider(
                    'gemini',
                    GeminiProvider(api_key=google_key, model='gemini-2.5-flash'),
                    default=not self.default_provider
                )
            except Exception as e:
                self.logger.error(f"Failed to setup Gemini from env: {e}")
                
        # Vertex AI setup
        if os.getenv('GOOGLE_CLOUD_PROJECT') and HAS_GENAI:
            try:
                self.register_provider(
                    'vertex_ai',
                    GeminiProvider(
                        vertex_ai=True,
                        project=os.getenv('GOOGLE_CLOUD_PROJECT'),
                        location=os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1'),
                        model='gemini-2.5-flash'
                    ),
                    default=not self.default_provider
                )
            except Exception as e:
                self.logger.error(f"Failed to setup Vertex AI from env: {e}")
        
    def register_provider(self, name: str, provider: LLMProvider, default: bool = False, fallback: bool = False):
        """
        Register an LLM provider.
        
        Args:
            name: Provider name
            provider: Provider instance
            default: Whether to set as default provider
            fallback: Whether to set as fallback provider
        """
        self.providers[name] = provider
        
        # Get rate limit from configuration
        config = get_config()
        provider_config = config.llm.providers.get(name)
        if provider_config and hasattr(provider_config, 'rate_limit_rpm'):
            rate_limit = provider_config.rate_limit_rpm
        else:
            rate_limit = 60  # default
        
        self.rate_limiters[name] = RateLimiter(calls_per_minute=rate_limit)
        
        if default or not self.default_provider:
            self.default_provider = name
            
        if fallback or not self.fallback_provider:
            self.fallback_provider = name
            
        self.logger.info(f"Registered LLM provider: {name} (default={default}, fallback={fallback})")
        
    async def generate_code_modification(
        self, 
        prompt: str, 
        llm_type: str = "flash",
        provider: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate code modifications using specified or default provider.
        
        Args:
            prompt: The prompt text to send to the LLM
            llm_type: Type of LLM to use ('flash' or 'pro') - for backward compatibility
            provider: Specific provider to use (overrides default)
            **kwargs: Additional parameters for the provider
            
        Returns:
            The LLM's response as a string, formatted as a diff
            
        Raises:
            ValueError: If provider not found
            RuntimeError: If API call fails
        """
        provider_name = provider or self.default_provider
        
        if not provider_name or provider_name not in self.providers:
            available = list(self.providers.keys())
            raise ValueError(f"Provider '{provider_name}' not found. Available: {available}")
            
        # Apply rate limiting
        await self.rate_limiters[provider_name].wait_if_needed()
        
        try:
            # Map llm_type to provider-specific parameters for backward compatibility
            if llm_type == "pro":
                if provider_name == "openai":
                    kwargs.setdefault('model', 'o4')
                elif provider_name == "anthropic":
                    kwargs.setdefault('model', 'claude-opus-4')
                elif provider_name in ["gemini", "vertex_ai"]:
                    kwargs.setdefault('model', 'gemini-2.5-pro')
            elif llm_type == "flash":
                if provider_name == "openai":
                    kwargs.setdefault('model', 'o1-mini')
                elif provider_name == "anthropic":
                    kwargs.setdefault('model', 'claude-3-5-sonnet-v2')
                elif provider_name in ["gemini", "vertex_ai"]:
                    kwargs.setdefault('model', 'gemini-2.5-flash')
            
            # For mock provider, pass llm_type directly
            if provider_name == "mock":
                kwargs['llm_type'] = llm_type
                
            response = await self.providers[provider_name].generate_code(prompt, **kwargs)
            self.logger.info(f"Generated code using {provider_name} ({response.model}) - tokens: {response.tokens_used}, cost: ${response.cost:.4f}")
            return response.content
            
        except Exception as e:
            self.logger.error(f"Error with provider {provider_name}: {e}")
            
            # Try fallback provider
            if self.fallback_provider and self.fallback_provider != provider_name:
                self.logger.warning(f"Falling back to {self.fallback_provider} provider")
                try:
                    await self.rate_limiters[self.fallback_provider].wait_if_needed()
                    response = await self.providers[self.fallback_provider].generate_code(prompt, **kwargs)
                    return response.content
                except Exception as fallback_error:
                    self.logger.error(f"Fallback provider {self.fallback_provider} also failed: {fallback_error}")
            
            raise RuntimeError(f"Error generating code modification: {str(e)}") from e
                
    async def critique_code(
        self,
        code: str,
        criteria: str = "correctness, performance, readability",
        provider: Optional[str] = None
    ) -> str:
        """
        Get code critique from LLM.
        
        Args:
            code: Code to critique
            criteria: Evaluation criteria
            provider: Specific provider to use
            
        Returns:
            Structured critique as string
        """
        provider_name = provider or self.default_provider
        
        if not provider_name or provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not found")
            
        await self.rate_limiters[provider_name].wait_if_needed()
        
        response = await self.providers[provider_name].critique_code(code, criteria)
        return response.content
        
    async def generate_with_response(
        self,
        prompt: str,
        provider: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Generate code and return full LLMResponse object.
        
        This method provides access to the complete response including
        metadata, thinking content, and cost information.
        
        Args:
            prompt: The prompt text
            provider: Specific provider to use
            **kwargs: Provider-specific parameters
            
        Returns:
            Complete LLMResponse object
        """
        provider_name = provider or self.default_provider
        
        if not provider_name or provider_name not in self.providers:
            available = list(self.providers.keys())
            raise ValueError(f"Provider '{provider_name}' not found. Available: {available}")
            
        await self.rate_limiters[provider_name].wait_if_needed()
        
        return await self.providers[provider_name].generate_code(prompt, **kwargs)
        
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())
        
    def get_default_provider(self) -> Optional[str]:
        """Get name of default provider."""
        return self.default_provider