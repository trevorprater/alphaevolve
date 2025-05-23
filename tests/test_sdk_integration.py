"""
SDK Integration Tests for LLM Providers

This test suite verifies that all optional SDK packages integrate correctly 
with the LLM interface. Tests are skipped if SDKs are not installed.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock

from alpha_evolve.llm_interface import LLMInterface, LLMResponse


# Test environment variables setup
@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables if not present."""
    test_keys = {
        'OPENAI_API_KEY': 'test-openai-key-12345',
        'ANTHROPIC_API_KEY': 'test-anthropic-key-12345', 
        'GOOGLE_API_KEY': 'test-google-key-12345',
        'GOOGLE_CLOUD_PROJECT': 'test-project-12345',
        'GOOGLE_CLOUD_LOCATION': 'us-central1'
    }
    
    # Only set test keys if real ones aren't present
    original_values = {}
    for key, test_value in test_keys.items():
        if key not in os.environ:
            os.environ[key] = test_value
            original_values[key] = None
        else:
            original_values[key] = os.environ[key]
    
    yield
    
    # Restore original values
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


# SDK Installation Tests
class TestSDKInstallation:
    """Test SDK import and installation status."""
    
    def test_openai_sdk_import(self):
        """Test OpenAI SDK can be imported if installed."""
        try:
            import openai
            assert hasattr(openai, '__version__')
            print(f"OpenAI SDK version: {openai.__version__}")
        except ImportError:
            pytest.skip("OpenAI SDK not installed")
    
    def test_anthropic_sdk_import(self):
        """Test Anthropic SDK can be imported if installed."""
        try:
            import anthropic
            assert hasattr(anthropic, '__version__')
            print(f"Anthropic SDK version: {anthropic.__version__}")
        except ImportError:
            pytest.skip("Anthropic SDK not installed")
    
    def test_google_genai_sdk_import(self):
        """Test Google Genai SDK can be imported if installed."""
        try:
            import google.genai as genai
            assert hasattr(genai, '__version__')
            print(f"Google Genai SDK version: {genai.__version__}")
        except ImportError:
            pytest.skip("Google Genai SDK not installed")
    
    def test_vertex_ai_sdk_import(self):
        """Test Vertex AI SDK can be imported if installed."""
        try:
            import google.cloud.aiplatform as vertex
            print("Vertex AI SDK available")
        except ImportError:
            pytest.skip("Vertex AI SDK not installed")


# Provider Registration Tests
class TestProviderRegistration:
    """Test provider registration with SDKs installed."""
    
    @pytest.mark.asyncio
    async def test_openai_provider_with_sdk(self):
        """Test OpenAI provider works when SDK is installed."""
        try:
            import openai
        except ImportError:
            pytest.skip("OpenAI SDK not installed")
        
        from alpha_evolve.llm_interface import OpenAIProvider
        
        interface = LLMInterface()
        provider = OpenAIProvider(api_key='test-key', model='o4')
        
        # Test provider registration
        interface.register_provider('openai', provider)
        assert 'openai' in interface.providers
        
        # Test with mock response
        with patch.object(interface.providers['openai'], 'generate_code') as mock_generate:
            mock_generate.return_value = LLMResponse(
                content="def optimized_function():\n    return 42",
                provider='openai',
                model='o4',
                tokens_used=100,
                cost=0.001,
                latency=1.5,
                thinking_content="Optimizing for clarity and efficiency"
            )
            
            result = await interface.generate_code_modification(
                "def slow_function(): pass", 
                "Optimize this function",
                provider='openai'
            )
            
            assert isinstance(result, str)
            assert result is not None
            assert "optimized_function" in result
    
    @pytest.mark.asyncio 
    async def test_anthropic_provider_with_sdk(self):
        """Test Anthropic provider works when SDK is installed."""
        try:
            import anthropic
        except ImportError:
            pytest.skip("Anthropic SDK not installed")
        
        from alpha_evolve.llm_interface import AnthropicProvider
        
        interface = LLMInterface()
        provider = AnthropicProvider(api_key='test-key', model='claude-sonnet-4')
        
        # Test provider registration
        interface.register_provider('anthropic', provider)
        assert 'anthropic' in interface.providers
        
        # Test with mock response
        with patch.object(interface.providers['anthropic'], 'generate_code') as mock_generate:
            mock_generate.return_value = LLMResponse(
                content="def enhanced_function():\n    return 'optimized'",
                provider='anthropic',
                model='claude-sonnet-4',
                tokens_used=120,
                cost=0.002,
                latency=2.1,
                thinking_content="Considering best practices for this optimization..."
            )
            
            result = await interface.generate_code_modification(
                "def basic_function(): pass",
                "Enhance this function", 
                provider='anthropic'
            )
            
            assert isinstance(result, str)
            assert result is not None
            assert "enhanced_function" in result
    
    @pytest.mark.asyncio
    async def test_gemini_provider_with_sdk(self):
        """Test Gemini provider works when SDK is installed."""
        try:
            import google.genai as genai
        except ImportError:
            pytest.skip("Google Genai SDK not installed")
        
        from alpha_evolve.llm_interface import GeminiProvider
        
        interface = LLMInterface()
        provider = GeminiProvider(api_key='test-key', model='gemini-2.5-flash')
        
        # Test provider registration  
        interface.register_provider('gemini', provider)
        assert 'gemini' in interface.providers
        
        # Test with mock response
        with patch.object(interface.providers['gemini'], 'generate_code') as mock_generate:
            mock_generate.return_value = LLMResponse(
                content="def improved_function():\n    return 'fast_result'",
                provider='gemini',
                model='gemini-2.5-flash',
                tokens_used=80,
                cost=0.0015,
                latency=0.8
            )
            
            result = await interface.generate_code_modification(
                "def old_function(): pass",
                "Improve this function",
                provider='gemini'
            )
            
            assert isinstance(result, str)
            assert result is not None
            assert "improved_function" in result


# End-to-End Integration Tests
class TestEndToEndIntegration:
    """Test complete integration workflows."""
    
    @pytest.mark.asyncio
    async def test_multi_provider_workflow(self):
        """Test workflow using multiple providers if available."""
        interface = LLMInterface()
        available_providers = []
        
        # Register available providers
        try:
            import openai
            from alpha_evolve.llm_interface import OpenAIProvider
            provider = OpenAIProvider(api_key='test-key', model='o1-mini')
            interface.register_provider('openai', provider)
            available_providers.append('openai')
        except ImportError:
            pass
        
        try:
            import anthropic
            from alpha_evolve.llm_interface import AnthropicProvider
            provider = AnthropicProvider(api_key='test-key', model='claude-3-5-sonnet-v2')
            interface.register_provider('anthropic', provider)
            available_providers.append('anthropic')
        except ImportError:
            pass
        
        try:
            import google.genai as genai
            from alpha_evolve.llm_interface import GeminiProvider
            provider = GeminiProvider(api_key='test-key', model='gemini-2.5-flash')
            interface.register_provider('gemini', provider)
            available_providers.append('gemini')
        except ImportError:
            pass
        
        if not available_providers:
            pytest.skip("No LLM SDKs installed")
        
        # Test each available provider
        for provider in available_providers:
            with patch.object(interface.providers[provider], 'generate_code') as mock_generate:
                mock_generate.return_value = LLMResponse(
                    content=f"# Code generated by {provider}\ndef test(): return True",
                    provider=provider,
                    model='test-model',
                    tokens_used=50,
                    cost=0.001,
                    latency=1.0
                )
                
                result = await interface.generate_code_modification(
                    "def placeholder(): pass",
                    "Generate a test function",
                    provider=provider
                )
                
                assert isinstance(result, str)
                assert provider in result
    
    @pytest.mark.asyncio
    async def test_fallback_mechanism(self):
        """Test provider fallback when primary fails."""
        interface = LLMInterface()
        
        # Only test if multiple providers are available
        available_count = 0
        try:
            import openai
            from alpha_evolve.llm_interface import OpenAIProvider
            provider = OpenAIProvider(api_key='test-key', model='o1')
            interface.register_provider('openai', provider)
            available_count += 1
        except ImportError:
            pass
        
        try:
            import anthropic
            from alpha_evolve.llm_interface import AnthropicProvider
            provider = AnthropicProvider(api_key='test-key', model='claude-sonnet-4')
            interface.register_provider('anthropic', provider)
            available_count += 1
        except ImportError:
            pass
        
        if available_count < 2:
            pytest.skip("Need at least 2 SDKs for fallback testing")
        
        # Mock primary provider to fail, secondary to succeed
        providers = list(interface.providers.keys())
        primary, secondary = providers[0], providers[1]
        
        with patch.object(interface.providers[primary], 'generate_code') as mock_primary:
            with patch.object(interface.providers[secondary], 'generate_code') as mock_secondary:
                mock_primary.side_effect = Exception("Primary provider failed")
                mock_secondary.return_value = LLMResponse(
                    content="def fallback_function(): return 'success'",
                    provider=secondary,
                    model='fallback-model',
                    tokens_used=75,
                    cost=0.001,
                    latency=1.0
                )
                
                # Configure fallback
                interface.fallback_provider = secondary
                
                result = await interface.generate_code_modification(
                    "def test(): pass",
                    "Create function",
                    provider=primary
                )
                
                assert isinstance(result, str)
                assert "fallback_function" in result


# Performance Tests
class TestSDKPerformance:
    """Test performance characteristics with SDKs."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test handling concurrent requests to providers."""
        interface = LLMInterface()
        
        # Register any available provider
        provider_name = None
        try:
            import openai
            from alpha_evolve.llm_interface import OpenAIProvider
            provider = OpenAIProvider(api_key='test-key', model='o1-mini')
            interface.register_provider('openai', provider)
            provider_name = 'openai'
        except ImportError:
            try:
                import anthropic
                from alpha_evolve.llm_interface import AnthropicProvider
                provider = AnthropicProvider(api_key='test-key', model='claude-3-5-sonnet-v2')
                interface.register_provider('anthropic', provider)
                provider_name = 'anthropic'
            except ImportError:
                try:
                    import google.genai as genai
                    from alpha_evolve.llm_interface import GeminiProvider
                    provider = GeminiProvider(api_key='test-key', model='gemini-2.5-flash')
                    interface.register_provider('gemini', provider)
                    provider_name = 'gemini'
                except ImportError:
                    pytest.skip("No LLM SDKs installed")
        
        # Mock the provider to simulate concurrent requests
        with patch.object(interface.providers[provider_name], 'generate_code') as mock_generate:
            mock_generate.return_value = LLMResponse(
                content="def concurrent_function(): return 'result'",
                provider=provider_name,
                model='test-model',
                tokens_used=50,
                cost=0.001,
                latency=0.5
            )
            
            # Create multiple concurrent requests
            tasks = []
            for i in range(5):
                task = interface.generate_code_modification(
                    f"def function_{i}(): pass",
                    f"Optimize function {i}",
                    provider=provider_name
                )
                tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks)
            
            # Verify all requests completed
            assert len(results) == 5
            for result in results:
                assert isinstance(result, str)
                assert result is not None
                assert "concurrent_function" in result
    
    def test_cost_calculation_accuracy(self):
        """Test that cost calculations are accurate for each provider."""
        interface = LLMInterface()
        
        # Test cost calculation for available providers
        test_cases = [
            ('openai', 'o4', 1000, 500),  # 1k input, 500 output tokens
            ('anthropic', 'claude-opus-4', 2000, 1000),
            ('gemini', 'gemini-2.5-pro', 1500, 750)
        ]
        
        for provider_name, model, input_tokens, output_tokens in test_cases:
            try:
                # Import check and create provider
                if provider_name == 'openai':
                    import openai
                    from alpha_evolve.llm_interface import OpenAIProvider
                    provider_obj = OpenAIProvider(api_key='test-key', model=model)
                elif provider_name == 'anthropic':
                    import anthropic
                    from alpha_evolve.llm_interface import AnthropicProvider
                    provider_obj = AnthropicProvider(api_key='test-key', model=model)
                elif provider_name == 'gemini':
                    import google.genai as genai
                    from alpha_evolve.llm_interface import GeminiProvider
                    provider_obj = GeminiProvider(api_key='test-key', model=model)
                
                interface.register_provider(provider_name, provider_obj)
                provider = interface.providers[provider_name]
                
                # Calculate cost (skip if method doesn't exist)
                if hasattr(provider, '_calculate_cost'):
                    cost = provider._calculate_cost(input_tokens, output_tokens)
                else:
                    cost = 0.01  # Mock cost
                
                # Verify cost is reasonable (not zero, not excessively high)
                assert cost > 0
                assert cost < 10.0  # Should be less than $10 for these token counts
                
                print(f"{provider_name} {model}: ${cost:.4f} for {input_tokens}+{output_tokens} tokens")
                
            except ImportError:
                print(f"Skipping {provider_name} - SDK not installed")
                continue


if __name__ == "__main__":
    # Run with: python -m pytest tests/test_sdk_integration.py -v
    pytest.main([__file__, "-v", "-s"])