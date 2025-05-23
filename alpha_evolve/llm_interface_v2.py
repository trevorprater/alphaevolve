"""
Advanced LLM Interface with support for multiple providers.

Supports:
- Anthropic (Claude) with thinking parameter
- OpenAI (GPT-4)
- Google Vertex AI (Gemini)
- Google Gemini API
"""
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Any, List, Union
from enum import Enum
import aiohttp
import os
from datetime import datetime, timedelta
import backoff
from collections import deque

from alpha_evolve.config import get_config


class RetryStrategy(Enum):
    """Retry strategies for failed requests."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    CONSTANT = "constant"


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    provider: str
    model: str
    tokens_used: Optional[Dict[str, int]] = None  # input, output, total
    cost: Optional[float] = None
    latency: Optional[float] = None
    thinking_content: Optional[str] = None  # For models that support thinking
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    api_key: str
    model: str
    base_url: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 2000
    timeout: int = 60
    max_retries: int = 3
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    rate_limit_rpm: int = 60
    additional_params: Dict[str, Any] = field(default_factory=dict)


class CircuitBreaker:
    """Circuit breaker pattern for handling provider failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
        
    def record_success(self):
        """Record a successful call."""
        self.failure_count = 0
        self.state = "closed"
        
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            
    def can_proceed(self) -> bool:
        """Check if requests can proceed."""
        if self.state == "closed":
            return True
            
        if self.state == "open":
            if self.last_failure_time and \
               datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                self.state = "half-open"
                return True
            return False
            
        # half-open state
        return True


class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = deque()
        self._lock = asyncio.Lock()
        
    async def acquire(self):
        """Acquire permission to make a call."""
        async with self._lock:
            now = time.time()
            # Remove calls older than 1 minute
            while self.calls and now - self.calls[0] >= 60:
                self.calls.popleft()
            
            if len(self.calls) >= self.calls_per_minute:
                sleep_time = 60 - (now - self.calls[0])
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    # Re-clean old calls
                    now = time.time()
                    while self.calls and now - self.calls[0] >= 60:
                        self.calls.popleft()
                    
            self.calls.append(now)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, config: ProviderConfig):
        """Initialize the LLM provider."""
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rate_limiter = RateLimiter(config.rate_limit_rpm)
        self.circuit_breaker = CircuitBreaker()
        
    @abstractmethod
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate code based on prompt."""
        pass
        
    @abstractmethod
    async def critique_code(self, code: str, criteria: str) -> LLMResponse:
        """Provide critique of code based on criteria."""
        pass
        
    def _get_retry_decorator(self):
        """Get retry decorator based on strategy."""
        if self.config.retry_strategy == RetryStrategy.EXPONENTIAL:
            return backoff.expo
        elif self.config.retry_strategy == RetryStrategy.LINEAR:
            return backoff.linear
        else:
            return backoff.constant
            
    async def _make_request_with_retry(self, request_func, *args, **kwargs):
        """Make request with retry logic."""
        retry_decorator = self._get_retry_decorator()
        
        @backoff.on_exception(
            retry_decorator,
            (aiohttp.ClientError, RuntimeError),
            max_tries=self.config.max_retries
        )
        async def _request():
            if not self.circuit_breaker.can_proceed():
                raise RuntimeError("Circuit breaker is open")
                
            try:
                result = await request_func(*args, **kwargs)
                self.circuit_breaker.record_success()
                return result
            except Exception as e:
                self.circuit_breaker.record_failure()
                raise
                
        return await _request()


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider with support for thinking parameter."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or 'https://api.anthropic.com/v1'
        
    async def _make_api_call(self, messages: List[Dict], **kwargs) -> Dict:
        """Make API call to Anthropic."""
        headers = {
            'x-api-key': self.config.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        payload = {
            'model': kwargs.get('model', self.config.model),
            'max_tokens': kwargs.get('max_tokens', self.config.max_tokens),
            'temperature': kwargs.get('temperature', self.config.temperature),
            'messages': messages
        }
        
        # Add thinking parameter if supported by model and requested
        if kwargs.get('use_thinking', False) and self._supports_thinking(payload['model']):
            payload['thinking'] = {
                'enabled': True,
                'budget_tokens': kwargs.get('thinking_budget', 8192)
            }
            
        # Add any additional parameters
        payload.update(self.config.additional_params)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/messages',
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Anthropic API error {response.status}: {error_text}")
                
                return await response.json()
                
    def _supports_thinking(self, model: str) -> bool:
        """Check if model supports thinking parameter."""
        thinking_models = [
            'claude-opus-4-20250514',
            'claude-sonnet-4-20250514',
            'claude-3-7-sonnet-20250219'
        ]
        return any(model.startswith(m) for m in thinking_models)
        
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate code using Anthropic Claude."""
        await self.rate_limiter.acquire()
        start_time = time.time()
        
        messages = [
            {
                'role': 'user',
                'content': f"You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.\n\n{prompt}"
            }
        ]
        
        result = await self._make_request_with_retry(
            self._make_api_call,
            messages,
            **kwargs
        )
        
        # Extract content and thinking if present
        content = ""
        thinking_content = None
        
        for block in result.get('content', []):
            if block['type'] == 'text':
                content = block['text']
            elif block['type'] == 'thinking':
                thinking_content = block.get('text', '')
                
        latency = time.time() - start_time
        
        # Calculate tokens and cost
        usage = result.get('usage', {})
        tokens_used = {
            'input': usage.get('input_tokens', 0),
            'output': usage.get('output_tokens', 0),
            'total': usage.get('total_tokens', 0)
        }
        
        # Rough cost estimation (adjust based on actual pricing)
        cost = self._calculate_cost(tokens_used, self.config.model)
        
        self.logger.info(f"Anthropic request completed in {latency:.2f}s")
        
        return LLMResponse(
            content=content,
            provider="anthropic",
            model=self.config.model,
            tokens_used=tokens_used,
            cost=cost,
            latency=latency,
            thinking_content=thinking_content,
            metadata={'thinking_enabled': kwargs.get('use_thinking', False)}
        )
        
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
        return await self.generate_code(prompt, use_thinking=True, thinking_budget=4096)
        
    def _calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        """Calculate approximate cost based on tokens."""
        # Pricing as of model release (adjust as needed)
        pricing = {
            'claude-3-opus': {'input': 0.015, 'output': 0.075},
            'claude-3-sonnet': {'input': 0.003, 'output': 0.015},
            'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},
            'claude-opus-4': {'input': 0.015, 'output': 0.075},
            'claude-sonnet-4': {'input': 0.003, 'output': 0.015},
        }
        
        # Find matching pricing
        for prefix, prices in pricing.items():
            if model.startswith(prefix):
                input_cost = (tokens['input'] / 1000) * prices['input']
                output_cost = (tokens['output'] / 1000) * prices['output']
                return input_cost + output_cost
                
        return 0.0  # Unknown model


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url or 'https://api.openai.com/v1'
        
    async def _make_api_call(self, messages: List[Dict], **kwargs) -> Dict:
        """Make API call to OpenAI."""
        headers = {
            'Authorization': f'Bearer {self.config.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': kwargs.get('model', self.config.model),
            'messages': messages,
            'temperature': kwargs.get('temperature', self.config.temperature),
            'max_tokens': kwargs.get('max_tokens', self.config.max_tokens)
        }
        
        # Add any additional parameters
        payload.update(self.config.additional_params)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"OpenAI API error {response.status}: {error_text}")
                
                return await response.json()
                
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate code using OpenAI."""
        await self.rate_limiter.acquire()
        start_time = time.time()
        
        messages = [
            {
                'role': 'system',
                'content': 'You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.'
            },
            {
                'role': 'user',
                'content': prompt
            }
        ]
        
        result = await self._make_request_with_retry(
            self._make_api_call,
            messages,
            **kwargs
        )
        
        content = result['choices'][0]['message']['content']
        latency = time.time() - start_time
        
        # Extract token usage
        usage = result.get('usage', {})
        tokens_used = {
            'input': usage.get('prompt_tokens', 0),
            'output': usage.get('completion_tokens', 0),
            'total': usage.get('total_tokens', 0)
        }
        
        cost = self._calculate_cost(tokens_used, self.config.model)
        
        self.logger.info(f"OpenAI request completed in {latency:.2f}s")
        
        return LLMResponse(
            content=content,
            provider="openai",
            model=self.config.model,
            tokens_used=tokens_used,
            cost=cost,
            latency=latency
        )
        
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
        
    def _calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        """Calculate approximate cost based on tokens."""
        # Pricing as of model release (adjust as needed)
        pricing = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
            'gpt-4o': {'input': 0.005, 'output': 0.015},
        }
        
        # Find matching pricing
        for prefix, prices in pricing.items():
            if model.startswith(prefix):
                input_cost = (tokens['input'] / 1000) * prices['input']
                output_cost = (tokens['output'] / 1000) * prices['output']
                return input_cost + output_cost
                
        return 0.0


class VertexAIProvider(LLMProvider):
    """Google Vertex AI provider for Gemini models."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Vertex AI requires google-cloud-aiplatform
        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel, GenerationConfig
            self.vertexai = vertexai
            self.GenerativeModel = GenerativeModel
            self.GenerationConfig = GenerationConfig
        except ImportError:
            raise ImportError(
                "google-cloud-aiplatform is required for Vertex AI. "
                "Install with: pip install google-cloud-aiplatform"
            )
            
        # Initialize Vertex AI
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT') or config.additional_params.get('project_id')
        location = config.additional_params.get('location', 'us-central1')
        
        if not project_id:
            raise ValueError("GOOGLE_CLOUD_PROJECT environment variable or project_id parameter required")
            
        self.vertexai.init(project=project_id, location=location)
        
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate code using Vertex AI Gemini."""
        await self.rate_limiter.acquire()
        start_time = time.time()
        
        # Create model
        model = self.GenerativeModel(
            model_name=kwargs.get('model', self.config.model)
        )
        
        # Generation config
        generation_config = self.GenerationConfig(
            temperature=kwargs.get('temperature', self.config.temperature),
            max_output_tokens=kwargs.get('max_tokens', self.config.max_tokens),
        )
        
        # Add system instruction
        full_prompt = f"""You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.

{prompt}"""
        
        # Generate response
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
            )
            
            content = response.text
            latency = time.time() - start_time
            
            # Extract token usage if available
            usage_metadata = response.usage_metadata
            tokens_used = {
                'input': usage_metadata.prompt_token_count,
                'output': usage_metadata.candidates_token_count,
                'total': usage_metadata.total_token_count
            }
            
            cost = self._calculate_cost(tokens_used, self.config.model)
            
            self.logger.info(f"Vertex AI request completed in {latency:.2f}s")
            
            return LLMResponse(
                content=content,
                provider="vertex_ai",
                model=self.config.model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency
            )
            
        except Exception as e:
            raise RuntimeError(f"Vertex AI error: {str(e)}")
            
    async def critique_code(self, code: str, criteria: str) -> LLMResponse:
        """Provide code critique using Vertex AI."""
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
        
    def _calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        """Calculate approximate cost for Vertex AI."""
        # Vertex AI Gemini pricing (adjust as needed)
        pricing = {
            'gemini-1.5-pro': {'input': 0.00125, 'output': 0.005},
            'gemini-1.5-flash': {'input': 0.00025, 'output': 0.001},
            'gemini-1.0-pro': {'input': 0.00025, 'output': 0.001},
        }
        
        for prefix, prices in pricing.items():
            if model.startswith(prefix):
                input_cost = (tokens['input'] / 1000) * prices['input']
                output_cost = (tokens['output'] / 1000) * prices['output']
                return input_cost + output_cost
                
        return 0.0


class GeminiProvider(LLMProvider):
    """Google Gemini API provider (standalone, not Vertex AI)."""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # Gemini API requires google-generativeai
        try:
            import google.generativeai as genai
            self.genai = genai
        except ImportError:
            raise ImportError(
                "google-generativeai is required for Gemini API. "
                "Install with: pip install google-generativeai"
            )
            
        # Configure API key
        self.genai.configure(api_key=config.api_key)
        
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate code using Gemini API."""
        await self.rate_limiter.acquire()
        start_time = time.time()
        
        # Create model
        model = self.genai.GenerativeModel(
            model_name=kwargs.get('model', self.config.model)
        )
        
        # Generation config
        generation_config = {
            'temperature': kwargs.get('temperature', self.config.temperature),
            'max_output_tokens': kwargs.get('max_tokens', self.config.max_tokens),
        }
        
        # Add system instruction
        full_prompt = f"""You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.

{prompt}"""
        
        try:
            # Generate response
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(
                    full_prompt,
                    generation_config=generation_config
                )
            )
            
            content = response.text
            latency = time.time() - start_time
            
            # Extract token usage if available
            tokens_used = {}
            if hasattr(response, 'usage_metadata'):
                tokens_used = {
                    'input': response.usage_metadata.prompt_token_count,
                    'output': response.usage_metadata.candidates_token_count,
                    'total': response.usage_metadata.total_token_count
                }
            
            cost = self._calculate_cost(tokens_used, self.config.model)
            
            self.logger.info(f"Gemini API request completed in {latency:.2f}s")
            
            return LLMResponse(
                content=content,
                provider="gemini",
                model=self.config.model,
                tokens_used=tokens_used,
                cost=cost,
                latency=latency
            )
            
        except Exception as e:
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
        
    def _calculate_cost(self, tokens: Dict[str, int], model: str) -> float:
        """Calculate approximate cost for Gemini API."""
        # Gemini API pricing (often has free tier)
        if not tokens:
            return 0.0
            
        # Adjust pricing based on actual Gemini API pricing
        pricing = {
            'gemini-pro': {'input': 0.0005, 'output': 0.0015},
            'gemini-1.5': {'input': 0.00025, 'output': 0.001},
        }
        
        for prefix, prices in pricing.items():
            if model.startswith(prefix):
                input_cost = (tokens.get('input', 0) / 1000) * prices['input']
                output_cost = (tokens.get('output', 0) / 1000) * prices['output']
                return input_cost + output_cost
                
        return 0.0


class MockProvider(LLMProvider):
    """Mock provider for testing."""
    
    def __init__(self, config: ProviderConfig):
        config.api_key = config.api_key or "mock"
        super().__init__(config)
        self.response_type = config.additional_params.get('response_type', 'flash')
        
    async def generate_code(self, prompt: str, **kwargs) -> LLMResponse:
        """Generate mock code response."""
        await asyncio.sleep(0.1)  # Simulate latency
        
        response_type = kwargs.get('llm_type', self.response_type)
        
        if response_type == "flash":
            content = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 3  # Mock LLM modified logic\n>>>>>>>> REPLACE"
        elif response_type == "pro":
            content = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 5  # Pro model enhanced logic\n>>>>>>>> REPLACE"
        else:
            content = "<<<<<<<< SEARCH\noriginal_code\n========\nmodified_code\n>>>>>>>> REPLACE"
            
        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
            tokens_used={'input': 100, 'output': 50, 'total': 150},
            cost=0.0,
            latency=0.1
        )
        
    async def critique_code(self, code: str, criteria: str) -> LLMResponse:
        """Provide mock critique."""
        await asyncio.sleep(0.1)
        content = '{"correctness": 8, "performance": 7, "readability": 9, "issues": "Minor optimization possible"}'
        
        return LLMResponse(
            content=content,
            provider="mock",
            model="mock-model",
            tokens_used={'input': 50, 'output': 25, 'total': 75},
            cost=0.0,
            latency=0.1
        )


class LLMInterface:
    """
    Advanced LLM interface with multiple providers and fallback support.
    """
    
    def __init__(self):
        """Initialize the LLM interface."""
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider = None
        self.fallback_chain: List[str] = []
        self.logger = logging.getLogger(__name__)
        
        # Initialize providers from configuration
        self._setup_providers()
        
    def _setup_providers(self):
        """Setup providers from configuration."""
        config = get_config()
        
        # Priority order for providers
        provider_priority = ['anthropic', 'openai', 'vertex_ai', 'gemini', 'mock']
        
        # Setup providers based on configuration
        for provider_name in provider_priority:
            if provider_name not in config.llm.providers:
                continue
                
            provider_config = config.llm.providers[provider_name]
            
            # Skip if no API key (except mock)
            if provider_name != 'mock' and not provider_config.api_key:
                continue
                
            try:
                # Create provider config
                config_obj = ProviderConfig(
                    api_key=provider_config.api_key or "",
                    model=provider_config.model,
                    base_url=getattr(provider_config, 'base_url', None),
                    temperature=getattr(provider_config, 'temperature', 0.2),
                    max_tokens=getattr(provider_config, 'max_tokens', 2000),
                    timeout=getattr(provider_config, 'timeout', 60),
                    max_retries=getattr(provider_config, 'max_retries', 3),
                    rate_limit_rpm=getattr(provider_config, 'rate_limit_rpm', 60)
                )
                
                # Create provider instance
                if provider_name == 'anthropic':
                    provider = AnthropicProvider(config_obj)
                elif provider_name == 'openai':
                    provider = OpenAIProvider(config_obj)
                elif provider_name == 'vertex_ai':
                    provider = VertexAIProvider(config_obj)
                elif provider_name == 'gemini':
                    provider = GeminiProvider(config_obj)
                elif provider_name == 'mock':
                    provider = MockProvider(config_obj)
                else:
                    self.logger.warning(f"Unknown provider type: {provider_name}")
                    continue
                    
                self.register_provider(provider_name, provider)
                
                # Set as default if specified or if it's the first provider
                if provider_name == config.llm.default_provider or not self.default_provider:
                    self.default_provider = provider_name
                    
            except Exception as e:
                self.logger.error(f"Failed to setup provider {provider_name}: {e}")
                
        # Setup fallback chain
        self._setup_fallback_chain()
        
        # Always ensure mock provider is available
        if 'mock' not in self.providers:
            mock_config = ProviderConfig(api_key="mock", model="mock-model")
            self.register_provider('mock', MockProvider(mock_config))
            
    def _setup_fallback_chain(self):
        """Setup fallback chain based on available providers."""
        # Default fallback order
        fallback_order = ['anthropic', 'openai', 'vertex_ai', 'gemini', 'mock']
        
        # Build chain from available providers
        self.fallback_chain = [
            provider for provider in fallback_order 
            if provider in self.providers
        ]
        
    def register_provider(self, name: str, provider: LLMProvider):
        """Register an LLM provider."""
        self.providers[name] = provider
        self.logger.info(f"Registered LLM provider: {name}")
        
    async def generate_code_modification(
        self,
        prompt: str,
        provider: Optional[str] = None,
        use_fallback: bool = True,
        **kwargs
    ) -> LLMResponse:
        """
        Generate code modifications with automatic fallback.
        
        Args:
            prompt: The prompt for code generation
            provider: Specific provider to use
            use_fallback: Whether to use fallback providers on failure
            **kwargs: Additional parameters for the provider
            
        Returns:
            LLMResponse with generated code
        """
        providers_to_try = []
        
        if provider:
            if provider not in self.providers:
                raise ValueError(f"Provider '{provider}' not found")
            providers_to_try = [provider]
            if use_fallback:
                # Add remaining fallback providers
                providers_to_try.extend([
                    p for p in self.fallback_chain 
                    if p != provider and p in self.providers
                ])
        else:
            # Use default provider with fallback chain
            if self.default_provider:
                providers_to_try = [self.default_provider]
                providers_to_try.extend([
                    p for p in self.fallback_chain 
                    if p != self.default_provider
                ])
            else:
                providers_to_try = self.fallback_chain
                
        last_error = None
        
        for provider_name in providers_to_try:
            try:
                self.logger.info(f"Attempting to use provider: {provider_name}")
                response = await self.providers[provider_name].generate_code(prompt, **kwargs)
                self.logger.info(f"Successfully generated code using {provider_name}")
                return response
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Provider {provider_name} failed: {e}")
                
                if not use_fallback:
                    break
                    
        # All providers failed
        raise RuntimeError(
            f"All providers failed. Last error: {str(last_error)}"
        )
        
    async def critique_code(
        self,
        code: str,
        criteria: str = "correctness, performance, readability",
        provider: Optional[str] = None,
        use_fallback: bool = True
    ) -> LLMResponse:
        """
        Get code critique with automatic fallback.
        
        Args:
            code: Code to critique
            criteria: Evaluation criteria
            provider: Specific provider to use
            use_fallback: Whether to use fallback providers
            
        Returns:
            LLMResponse with critique
        """
        providers_to_try = []
        
        if provider:
            if provider not in self.providers:
                raise ValueError(f"Provider '{provider}' not found")
            providers_to_try = [provider]
            if use_fallback:
                providers_to_try.extend([
                    p for p in self.fallback_chain 
                    if p != provider and p in self.providers
                ])
        else:
            providers_to_try = [self.default_provider] if self.default_provider else []
            providers_to_try.extend([
                p for p in self.fallback_chain 
                if p != self.default_provider
            ])
            
        last_error = None
        
        for provider_name in providers_to_try:
            try:
                self.logger.info(f"Attempting critique with provider: {provider_name}")
                response = await self.providers[provider_name].critique_code(code, criteria)
                self.logger.info(f"Successfully critiqued code using {provider_name}")
                return response
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Provider {provider_name} failed: {e}")
                
                if not use_fallback:
                    break
                    
        raise RuntimeError(
            f"All providers failed. Last error: {str(last_error)}"
        )
        
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())
        
    def get_provider_info(self, provider: str) -> Dict[str, Any]:
        """Get information about a specific provider."""
        if provider not in self.providers:
            raise ValueError(f"Provider '{provider}' not found")
            
        provider_obj = self.providers[provider]
        return {
            'name': provider,
            'model': provider_obj.config.model,
            'rate_limit': provider_obj.config.rate_limit_rpm,
            'circuit_breaker_state': provider_obj.circuit_breaker.state,
            'supports_thinking': hasattr(provider_obj, '_supports_thinking')
        }
        
    def get_default_provider(self) -> Optional[str]:
        """Get name of default provider."""
        return self.default_provider