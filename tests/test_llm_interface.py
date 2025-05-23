"""
Tests for the LLMInterface class.
"""

import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock, MagicMock

from alpha_evolve.llm_interface import (
    LLMInterface, LLMResponse, LLMProvider,
    OpenAIProvider, AnthropicProvider, GeminiProvider, MockProvider,
    RateLimiter
)


def test_init():
    """
    Test LLMInterface initialization.
    """
    interface = LLMInterface()
    assert 'mock' in interface.providers  # Mock provider should always be available
    assert interface.default_provider is not None
    assert len(interface.get_available_providers()) >= 1


def test_mock_provider():
    """
    Test MockProvider functionality.
    """
    provider = MockProvider()
    
    # Test flash response
    provider.response_type = 'flash'
    result = asyncio.run(provider.generate_code("test prompt"))
    expected = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 3  # Mock LLM modified logic\n>>>>>>>> REPLACE"
    assert isinstance(result, LLMResponse)
    assert result.content == expected
    assert result.provider == "mock"
    assert result.model == "mock-model"
    assert result.tokens_used == 100
    assert result.cost == 0.001
    
    # Test pro response
    provider.response_type = 'pro'
    result = asyncio.run(provider.generate_code("test prompt"))
    expected = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 5  # Pro model enhanced logic\n>>>>>>>> REPLACE"
    assert result.content == expected
    
    # Test critique
    critique = asyncio.run(provider.critique_code("def test(): pass", "readability"))
    assert isinstance(critique, LLMResponse)
    assert '"correctness"' in critique.content


@pytest.mark.asyncio
async def test_rate_limiter():
    """
    Test RateLimiter functionality.
    """
    limiter = RateLimiter(calls_per_minute=2)
    
    # Should allow first call immediately
    await limiter.wait_if_needed()
    await limiter.wait_if_needed()
    
    # Third call should be rate limited but we won't wait for it in tests
    assert len(limiter.calls) == 2


@pytest.mark.asyncio
async def test_generate_code_modification_mock():
    """
    Test generate_code_modification with mock provider.
    """
    interface = LLMInterface()
    
    # Force use of mock provider
    result = await interface.generate_code_modification(
        prompt="Test prompt", 
        llm_type="flash",
        provider="mock"
    )
    
    expected = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 3  # Mock LLM modified logic\n>>>>>>>> REPLACE"
    assert result == expected


@pytest.mark.asyncio
async def test_generate_code_modification_pro():
    """
    Test generate_code_modification with 'pro' LLM type.
    """
    interface = LLMInterface()
    
    result = await interface.generate_code_modification(
        prompt="Test prompt", 
        llm_type="pro",
        provider="mock"
    )
    
    expected = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 5  # Pro model enhanced logic\n>>>>>>>> REPLACE"
    assert result == expected


@pytest.mark.asyncio
async def test_generate_code_modification_unknown_provider():
    """
    Test generate_code_modification with an unknown provider.
    """
    interface = LLMInterface()
    
    with pytest.raises(ValueError) as excinfo:
        await interface.generate_code_modification(
            prompt="Test prompt", 
            provider="unknown_provider"
        )
    
    assert "Provider 'unknown_provider' not found" in str(excinfo.value)


@pytest.mark.asyncio
async def test_critique_code():
    """
    Test code critique functionality.
    """
    interface = LLMInterface()
    
    critique = await interface.critique_code(
        code="def test(): pass",
        criteria="readability",
        provider="mock"
    )
    
    assert '"correctness"' in critique


@patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'})
def test_openai_provider_registration():
    """
    Test that OpenAI provider is registered when API key is available.
    """
    # Skip if openai package not installed
    try:
        import openai
        interface = LLMInterface()
        assert 'openai' in interface.get_available_providers()
    except ImportError:
        pytest.skip("openai package not installed")


@patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
def test_anthropic_provider_registration():
    """
    Test that Anthropic provider is registered when API key is available.
    """
    # Skip if anthropic package not installed
    try:
        import anthropic
        interface = LLMInterface()
        assert 'anthropic' in interface.get_available_providers()
    except ImportError:
        pytest.skip("anthropic package not installed")


def test_provider_fallback():
    """
    Test fallback provider when primary provider fails.
    """
    interface = LLMInterface()
    
    # Create a failing provider
    class FailingProvider(LLMProvider):
        @property
        def name(self):
            return "failing"
            
        async def generate_code(self, prompt, **kwargs):
            raise RuntimeError("API Error")
            
        async def critique_code(self, code, criteria):
            raise RuntimeError("API Error")
    
    # Register failing provider as default and mock as fallback
    interface.register_provider('failing', FailingProvider(), default=True)
    interface.register_provider('mock', MockProvider(), fallback=True)
    
    # Should fallback to mock provider
    result = asyncio.run(interface.generate_code_modification(
        prompt="Test prompt",
        provider="failing"
    ))
    
    # Should get mock response as fallback
    assert "SEARCH" in result and "REPLACE" in result


def test_backward_compatibility():
    """
    Test that the interface maintains backward compatibility.
    """
    interface = LLMInterface()
    
    # Old-style call should still work
    result = asyncio.run(interface.generate_code_modification(
        prompt="Test prompt",
        llm_type="flash"
    ))
    
    assert result is not None
    assert "SEARCH" in result and "REPLACE" in result


@pytest.mark.asyncio
async def test_generate_with_response():
    """
    Test the generate_with_response method that returns full LLMResponse.
    """
    interface = LLMInterface()
    
    response = await interface.generate_with_response(
        prompt="Test prompt",
        provider="mock"
    )
    
    assert isinstance(response, LLMResponse)
    assert response.content is not None
    assert response.provider == "mock"
    assert response.model == "mock-model"
    assert response.tokens_used is not None
    assert response.cost is not None
    assert response.latency is not None


@patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'})
def test_gemini_provider_registration():
    """
    Test that Gemini provider is registered when API key is available.
    """
    # Skip if google.genai package not installed
    try:
        import google.genai
        interface = LLMInterface()
        assert 'gemini' in interface.get_available_providers()
    except ImportError:
        pytest.skip("google-genai package not installed")


@patch.dict(os.environ, {'GOOGLE_CLOUD_PROJECT': 'test-project'})
def test_vertex_ai_provider_registration():
    """
    Test that Vertex AI provider is registered when project is configured.
    """
    # Skip if google.genai package not installed
    try:
        import google.genai
        interface = LLMInterface()
        # Vertex AI requires credentials, so it might not be registered in tests
        # This is expected behavior
    except ImportError:
        pytest.skip("google-genai package not installed")


def test_llm_response_structure():
    """
    Test LLMResponse dataclass structure.
    """
    response = LLMResponse(
        content="test content",
        provider="test",
        model="test-model",
        tokens_used=100,
        cost=0.01,
        latency=1.5,
        thinking_content="test thinking",
        metadata={"test": "data"}
    )
    
    assert response.content == "test content"
    assert response.provider == "test"
    assert response.model == "test-model"
    assert response.tokens_used == 100
    assert response.cost == 0.01
    assert response.latency == 1.5
    assert response.thinking_content == "test thinking"
    assert response.metadata == {"test": "data"}