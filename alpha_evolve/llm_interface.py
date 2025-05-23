"""
Interface for interacting with Large Language Models for code generation.
"""
import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional, Any, List
import aiohttp
import os
from enum import Enum


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, **config):
        """
        Initialize the LLM provider.
        
        Args:
            api_key: API key for the provider
            **config: Provider-specific configuration
        """
        self.api_key = api_key
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    async def generate_code(self, prompt: str, **kwargs) -> str:
        """
        Generate code based on prompt.
        
        Args:
            prompt: The input prompt for code generation
            **kwargs: Provider-specific parameters
            
        Returns:
            Generated code or diff as string
        """
        pass
        
    @abstractmethod
    async def critique_code(self, code: str, criteria: str) -> str:
        """
        Provide critique of code based on criteria.
        
        Args:
            code: The code to critique
            criteria: Criteria for evaluation
            
        Returns:
            Structured critique as string
        """
        pass


@dataclass
class LLMResponse:
    """Response from an LLM provider."""
    content: str
    provider: str
    model: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    latency: Optional[float] = None


class OpenAIProvider(LLMProvider):
    """OpenAI-specific implementation."""
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        self.base_url = config.get('base_url', 'https://api.openai.com/v1')
        self.model = config.get('model', 'gpt-4')
        self.temperature = config.get('temperature', 0.2)
        self.max_tokens = config.get('max_tokens', 2000)
        
    async def generate_code(self, prompt: str, **kwargs) -> str:
        """Generate code using OpenAI API."""
        start_time = time.time()
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': kwargs.get('model', self.model),
            'messages': [
                {
                    'role': 'system',
                    'content': 'You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.'
                },
                {
                    'role': 'user', 
                    'content': prompt
                }
            ],
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/chat/completions',
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"OpenAI API error {response.status}: {error_text}")
                
                result = await response.json()
                content = result['choices'][0]['message']['content']
                
                latency = time.time() - start_time
                self.logger.info(f"OpenAI request completed in {latency:.2f}s")
                
                return content
                
    async def critique_code(self, code: str, criteria: str) -> str:
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
    """Anthropic Claude-specific implementation."""
    
    def __init__(self, api_key: str, **config):
        super().__init__(api_key, **config)
        self.base_url = config.get('base_url', 'https://api.anthropic.com/v1')
        self.model = config.get('model', 'claude-3-sonnet-20240229')
        self.max_tokens = config.get('max_tokens', 2000)
        
    async def generate_code(self, prompt: str, **kwargs) -> str:
        """Generate code using Anthropic Claude API."""
        start_time = time.time()
        
        headers = {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        payload = {
            'model': kwargs.get('model', self.model),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            'messages': [
                {
                    'role': 'user',
                    'content': f"You are a code optimization expert. Generate precise code modifications in SEARCH/REPLACE format.\n\n{prompt}"
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{self.base_url}/messages',
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(f"Anthropic API error {response.status}: {error_text}")
                
                result = await response.json()
                content = result['content'][0]['text']
                
                latency = time.time() - start_time
                self.logger.info(f"Anthropic request completed in {latency:.2f}s")
                
                return content
                
    async def critique_code(self, code: str, criteria: str) -> str:
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


class MockProvider(LLMProvider):
    """Mock provider for testing."""
    
    def __init__(self, api_key: str = "mock", **config):
        super().__init__(api_key, **config)
        self.response_type = config.get('response_type', 'flash')
        
    async def generate_code(self, prompt: str, **kwargs) -> str:
        """Generate mock code response."""
        await asyncio.sleep(0.1)  # Simulate latency
        
        # Check for llm_type in kwargs for backward compatibility
        response_type = kwargs.get('llm_type', self.response_type)
        
        if response_type == "flash":
            return "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 3  # Mock LLM modified logic\n>>>>>>>> REPLACE"
        elif response_type == "pro":
            return "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 5  # Pro model enhanced logic\n>>>>>>>> REPLACE"
        else:
            return "<<<<<<<< SEARCH\noriginal_code\n========\nmodified_code\n>>>>>>>> REPLACE"
            
    async def critique_code(self, code: str, criteria: str) -> str:
        """Provide mock critique."""
        await asyncio.sleep(0.1)
        return '{"correctness": 8, "performance": 7, "readability": 9, "issues": "Minor optimization possible"}'


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
    """
    
    def __init__(self):
        """Initialize the LLM interface."""
        self.providers: Dict[str, LLMProvider] = {}
        self.default_provider = None
        self.rate_limiters: Dict[str, RateLimiter] = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize providers from environment variables
        self._setup_providers()
        
    def _setup_providers(self):
        """Setup providers from environment variables."""
        # OpenAI setup
        openai_key = os.getenv('OPENAI_API_KEY')
        if openai_key:
            self.register_provider(
                'openai', 
                OpenAIProvider(openai_key, model='gpt-4'),
                default=True
            )
            
        # Anthropic setup  
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if anthropic_key:
            self.register_provider(
                'anthropic',
                AnthropicProvider(anthropic_key),
                default=not self.default_provider  # Use as default if no OpenAI
            )
            
        # Always have mock provider as fallback
        self.register_provider(
            'mock',
            MockProvider(),
            default=not self.default_provider  # Use as default if no real providers
        )
        
    def register_provider(self, name: str, provider: LLMProvider, default: bool = False):
        """
        Register an LLM provider.
        
        Args:
            name: Provider name
            provider: Provider instance
            default: Whether to set as default provider
        """
        self.providers[name] = provider
        self.rate_limiters[name] = RateLimiter()
        
        if default or not self.default_provider:
            self.default_provider = name
            
        self.logger.info(f"Registered LLM provider: {name}")
        
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
            if llm_type == "pro" and provider_name == "openai":
                kwargs.setdefault('model', 'gpt-4')
                kwargs.setdefault('temperature', 0.1)
            elif llm_type == "flash" and provider_name == "openai":
                kwargs.setdefault('model', 'gpt-3.5-turbo')
                kwargs.setdefault('temperature', 0.3)
            
            # For mock provider, pass llm_type directly
            if provider_name == "mock":
                kwargs['llm_type'] = llm_type
                
            result = await self.providers[provider_name].generate_code(prompt, **kwargs)
            self.logger.info(f"Generated code using {provider_name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error with provider {provider_name}: {e}")
            
            # Try fallback to mock provider if not already using it
            if provider_name != 'mock' and 'mock' in self.providers:
                self.logger.warning("Falling back to mock provider")
                return await self.providers['mock'].generate_code(prompt, **kwargs)
            else:
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
        
        return await self.providers[provider_name].critique_code(code, criteria)
        
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self.providers.keys())
        
    def get_default_provider(self) -> Optional[str]:
        """Get name of default provider."""
        return self.default_provider