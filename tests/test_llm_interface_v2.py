"""Tests for the advanced LLM interface."""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime, timedelta

from alpha_evolve.llm_interface_v2 import (
    LLMInterface, LLMResponse, ProviderConfig, RetryStrategy,
    AnthropicProvider, OpenAIProvider, VertexAIProvider, GeminiProvider,
    MockProvider, CircuitBreaker, RateLimiter
)


class TestCircuitBreaker:
    """Test circuit breaker functionality."""
    
    def test_circuit_breaker_closed_initially(self):
        """Test circuit breaker starts in closed state."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        assert breaker.state == "closed"
        assert breaker.can_proceed() is True
        
    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
        
        # Record failures
        for _ in range(3):
            breaker.record_failure()
            
        assert breaker.state == "open"
        assert breaker.can_proceed() is False
        
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovery after timeout."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        
        # Open the breaker
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "open"
        
        # Wait for recovery
        import time
        time.sleep(0.2)
        
        # Should be able to proceed (half-open)
        assert breaker.can_proceed() is True
        assert breaker.state == "half-open"
        
        # Success should close it
        breaker.record_success()
        assert breaker.state == "closed"


class TestRateLimiter:
    """Test rate limiter functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_calls_under_limit(self):
        """Test rate limiter allows calls under limit."""
        limiter = RateLimiter(calls_per_minute=10)
        
        # Should allow 5 calls without delay
        for _ in range(5):
            await limiter.acquire()
            
    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_limit(self):
        """Test rate limiter enforces limit."""
        limiter = RateLimiter(calls_per_minute=2)
        
        # Make 2 calls quickly
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        await limiter.acquire()
        
        # Third call should be delayed
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start_time
        
        # Should have waited (with some tolerance for test execution)
        assert elapsed >= 50  # At least 50 seconds wait


class TestLLMResponse:
    """Test LLMResponse dataclass."""
    
    def test_llm_response_creation(self):
        """Test creating LLM response."""
        response = LLMResponse(
            content="Generated code",
            provider="openai",
            model="gpt-4",
            tokens_used={'input': 100, 'output': 50, 'total': 150},
            cost=0.01,
            latency=2.5
        )
        
        assert response.content == "Generated code"
        assert response.provider == "openai"
        assert response.tokens_used['total'] == 150
        assert response.cost == 0.01
        
    def test_llm_response_with_thinking(self):
        """Test LLM response with thinking content."""
        response = LLMResponse(
            content="Final answer",
            provider="anthropic",
            model="claude-3-opus",
            thinking_content="Step 1: Analyze...\nStep 2: Consider..."
        )
        
        assert response.thinking_content is not None
        assert "Step 1" in response.thinking_content


class TestAnthropicProvider:
    """Test Anthropic provider."""
    
    @pytest.fixture
    def provider_config(self):
        return ProviderConfig(
            api_key="test-key",
            model="claude-3-sonnet-20240229",
            temperature=0.2,
            max_tokens=2000
        )
        
    def test_supports_thinking_detection(self, provider_config):
        """Test detection of models that support thinking."""
        provider = AnthropicProvider(provider_config)
        
        # Models that should support thinking
        assert provider._supports_thinking("claude-opus-4-20250514") is True
        assert provider._supports_thinking("claude-sonnet-4-20250514") is True
        assert provider._supports_thinking("claude-3-7-sonnet-20250219") is True
        
        # Models that shouldn't
        assert provider._supports_thinking("claude-3-sonnet-20240229") is False
        assert provider._supports_thinking("claude-instant") is False
        
    @pytest.mark.asyncio
    async def test_generate_code_with_thinking(self, provider_config):
        """Test code generation with thinking parameter."""
        provider = AnthropicProvider(provider_config)
        
        # Mock the API call
        mock_response = {
            'content': [
                {'type': 'thinking', 'text': 'Let me think about this...'},
                {'type': 'text', 'text': 'Generated code here'}
            ],
            'usage': {
                'input_tokens': 100,
                'output_tokens': 200,
                'total_tokens': 300
            }
        }
        
        with patch.object(provider, '_make_api_call', return_value=mock_response):
            response = await provider.generate_code(
                "Generate a function",
                use_thinking=True,
                thinking_budget=8192
            )
            
            assert response.content == "Generated code here"
            assert response.thinking_content == "Let me think about this..."
            assert response.metadata['thinking_enabled'] is True
            
    def test_cost_calculation(self, provider_config):
        """Test cost calculation for different models."""
        provider = AnthropicProvider(provider_config)
        
        tokens = {'input': 1000, 'output': 500, 'total': 1500}
        
        # Test Claude 3 Sonnet pricing
        cost = provider._calculate_cost(tokens, 'claude-3-sonnet-20240229')
        expected_cost = (1000/1000 * 0.003) + (500/1000 * 0.015)
        assert abs(cost - expected_cost) < 0.0001


class TestOpenAIProvider:
    """Test OpenAI provider."""
    
    @pytest.fixture
    def provider_config(self):
        return ProviderConfig(
            api_key="test-key",
            model="gpt-4",
            temperature=0.2,
            max_tokens=2000
        )
        
    @pytest.mark.asyncio
    async def test_generate_code_basic(self, provider_config):
        """Test basic code generation."""
        provider = OpenAIProvider(provider_config)
        
        # Mock the API call
        mock_response = {
            'choices': [{
                'message': {'content': 'Generated code'}
            }],
            'usage': {
                'prompt_tokens': 100,
                'completion_tokens': 50,
                'total_tokens': 150
            }
        }
        
        with patch.object(provider, '_make_api_call', return_value=mock_response):
            response = await provider.generate_code("Generate a function")
            
            assert response.content == "Generated code"
            assert response.provider == "openai"
            assert response.tokens_used['total'] == 150


class TestMockProvider:
    """Test mock provider."""
    
    @pytest.mark.asyncio
    async def test_mock_provider_flash_response(self):
        """Test mock provider flash response."""
        config = ProviderConfig(
            api_key="mock",
            model="mock-model",
            additional_params={'response_type': 'flash'}
        )
        provider = MockProvider(config)
        
        response = await provider.generate_code("Test prompt")
        assert "input_x * 3" in response.content
        assert response.provider == "mock"
        
    @pytest.mark.asyncio
    async def test_mock_provider_pro_response(self):
        """Test mock provider pro response."""
        config = ProviderConfig(
            api_key="mock",
            model="mock-model",
            additional_params={'response_type': 'pro'}
        )
        provider = MockProvider(config)
        
        response = await provider.generate_code("Test prompt", llm_type="pro")
        assert "input_x * 5" in response.content


class TestLLMInterface:
    """Test the main LLM interface."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = Mock()
        config.llm.providers = {
            'mock': Mock(
                api_key='mock',
                model='mock-model',
                temperature=0.2,
                max_tokens=2000,
                timeout=60,
                max_retries=3,
                rate_limit_rpm=60
            )
        }
        config.llm.default_provider = 'mock'
        return config
        
    @pytest.mark.asyncio
    async def test_generate_code_with_default_provider(self, mock_config):
        """Test code generation with default provider."""
        with patch('alpha_evolve.llm_interface_v2.get_config', return_value=mock_config):
            interface = LLMInterface()
            
            response = await interface.generate_code_modification("Test prompt")
            assert response.provider == "mock"
            assert response.content is not None
            
    @pytest.mark.asyncio
    async def test_generate_code_with_specific_provider(self, mock_config):
        """Test code generation with specific provider."""
        with patch('alpha_evolve.llm_interface_v2.get_config', return_value=mock_config):
            interface = LLMInterface()
            
            response = await interface.generate_code_modification(
                "Test prompt",
                provider="mock"
            )
            assert response.provider == "mock"
            
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self):
        """Test fallback mechanism when primary provider fails."""
        # Create interface with multiple providers
        interface = LLMInterface()
        
        # Mock providers
        failing_provider = AsyncMock()
        failing_provider.generate_code.side_effect = RuntimeError("API Error")
        
        working_provider = AsyncMock()
        working_provider.generate_code.return_value = LLMResponse(
            content="Fallback response",
            provider="mock",
            model="mock-model"
        )
        
        # Register providers
        interface.providers = {
            'primary': failing_provider,
            'mock': working_provider
        }
        interface.default_provider = 'primary'
        interface.fallback_chain = ['primary', 'mock']
        
        # Should fallback to mock
        response = await interface.generate_code_modification("Test prompt")
        assert response.content == "Fallback response"
        assert response.provider == "mock"
        
    def test_get_available_providers(self, mock_config):
        """Test getting list of available providers."""
        with patch('alpha_evolve.llm_interface_v2.get_config', return_value=mock_config):
            interface = LLMInterface()
            providers = interface.get_available_providers()
            assert 'mock' in providers
            
    def test_get_provider_info(self, mock_config):
        """Test getting provider information."""
        with patch('alpha_evolve.llm_interface_v2.get_config', return_value=mock_config):
            interface = LLMInterface()
            info = interface.get_provider_info('mock')
            
            assert info['name'] == 'mock'
            assert info['model'] == 'mock-model'
            assert info['circuit_breaker_state'] == 'closed'


@pytest.mark.asyncio
async def test_retry_mechanism():
    """Test retry mechanism with backoff."""
    config = ProviderConfig(
        api_key="test",
        model="test-model",
        max_retries=3,
        retry_strategy=RetryStrategy.EXPONENTIAL
    )
    
    # Create a provider with mocked request
    provider = OpenAIProvider(config)
    
    call_count = 0
    
    async def failing_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RuntimeError("Temporary failure")
        return {'choices': [{'message': {'content': 'Success'}}], 'usage': {}}
    
    # Patch the actual request method
    with patch.object(provider, '_make_api_call', side_effect=failing_request):
        with patch('alpha_evolve.llm_interface_v2.backoff.expo'):
            response = await provider.generate_code("Test")
            assert call_count == 3  # Should retry twice before succeeding


@pytest.mark.asyncio
async def test_concurrent_requests_with_rate_limiting():
    """Test handling concurrent requests with rate limiting."""
    interface = LLMInterface()
    
    # Configure mock provider with low rate limit
    mock_provider = MockProvider(ProviderConfig(
        api_key="mock",
        model="mock",
        rate_limit_rpm=2  # Very low for testing
    ))
    
    interface.providers = {'mock': mock_provider}
    interface.default_provider = 'mock'
    
    # Make concurrent requests
    start_time = asyncio.get_event_loop().time()
    
    tasks = [
        interface.generate_code_modification(f"Prompt {i}")
        for i in range(3)
    ]
    
    responses = await asyncio.gather(*tasks)
    
    # All should succeed
    assert len(responses) == 3
    assert all(r.provider == "mock" for r in responses)
    
    # But should have been rate limited
    elapsed = asyncio.get_event_loop().time() - start_time
    assert elapsed >= 50  # At least some delay due to rate limiting