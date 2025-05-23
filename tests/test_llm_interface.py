"""
Tests for the LLMInterface class.
"""

import pytest
import asyncio
import os
from unittest.mock import patch, AsyncMock

from alpha_evolve.llm_interface import LLMInterface, OpenAIProvider, AnthropicProvider, MockProvider, RateLimiter


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
    assert result == expected
    
    # Test pro response
    provider.response_type = 'pro'
    result = asyncio.run(provider.generate_code("test prompt"))
    expected = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 5  # Pro model enhanced logic\n>>>>>>>> REPLACE"
    assert result == expected
    
    # Test critique
    critique = asyncio.run(provider.critique_code("def test(): pass", "readability"))
    assert '"correctness"' in critique


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
    interface = LLMInterface()
    assert 'openai' in interface.get_available_providers()


@patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-key'})
def test_anthropic_provider_registration():
    """
    Test that Anthropic provider is registered when API key is available.
    """
    interface = LLMInterface()
    assert 'anthropic' in interface.get_available_providers()


def test_provider_fallback():
    """
    Test fallback to mock provider when real provider fails.
    """
    interface = LLMInterface()
    
    # Mock a provider that will fail
    failing_provider = MockProvider()
    failing_provider.generate_code = AsyncMock(side_effect=Exception("API Error"))
    interface.register_provider('failing', failing_provider)
    
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