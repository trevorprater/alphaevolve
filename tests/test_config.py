"""
Tests for the configuration management system.
"""

import os
import pytest
import tempfile
import yaml
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from alpha_evolve.config import (
    LLMProviderConfig,
    LLMConfig,
    SandboxConfig,
    DatabaseConfig,
    EvolutionConfig,
    LoggingConfig,
    SecurityConfig,
    AlphaEvolveConfig,
    ConfigManager,
    get_config_manager,
    get_config,
    reload_config
)


class TestLLMProviderConfig:
    """Test LLMProviderConfig model."""
    
    def test_valid_config(self):
        """Test valid LLM provider configuration."""
        config = LLMProviderConfig(
            api_key="test-key",
            model="gpt-4",
            temperature=0.5,
            max_tokens=1000
        )
        
        assert config.api_key == "test-key"
        assert config.model == "gpt-4"
        assert config.temperature == 0.5
        assert config.max_tokens == 1000
        assert config.timeout_seconds == 30  # default
        assert config.rate_limit_rpm == 60  # default
    
    def test_temperature_validation(self):
        """Test temperature validation."""
        # Valid temperatures
        LLMProviderConfig(model="test", temperature=0.0)
        LLMProviderConfig(model="test", temperature=1.0)
        LLMProviderConfig(model="test", temperature=2.0)
        
        # Invalid temperatures should raise validation errors
        with pytest.raises(ValueError):
            LLMProviderConfig(model="test", temperature=-0.1)
        with pytest.raises(ValueError):
            LLMProviderConfig(model="test", temperature=2.1)
    
    def test_max_tokens_validation(self):
        """Test max_tokens validation."""
        # Valid max_tokens
        LLMProviderConfig(model="test", max_tokens=1)
        LLMProviderConfig(model="test", max_tokens=10000)
        
        # Invalid max_tokens
        with pytest.raises(ValueError):
            LLMProviderConfig(model="test", max_tokens=0)
        with pytest.raises(ValueError):
            LLMProviderConfig(model="test", max_tokens=-1)


class TestLLMConfig:
    """Test LLMConfig model."""
    
    def test_valid_config(self):
        """Test valid LLM configuration."""
        config = LLMConfig(
            default_provider="openai",
            providers={
                "openai": LLMProviderConfig(model="gpt-4"),
                "anthropic": LLMProviderConfig(model="claude-3")
            }
        )
        
        assert config.default_provider == "openai"
        assert "openai" in config.providers
        assert "anthropic" in config.providers
    
    def test_provider_validation(self):
        """Test provider validation."""
        # Valid: default provider exists in providers
        LLMConfig(
            default_provider="openai",
            providers={"openai": LLMProviderConfig(model="gpt-4")}
        )
        
        # Valid: mock provider doesn't need to be in providers
        LLMConfig(
            default_provider="mock",
            providers={"openai": LLMProviderConfig(model="gpt-4")}
        )
        
        # Invalid: default provider not in providers
        with pytest.raises(ValueError):
            LLMConfig(
                default_provider="nonexistent",
                providers={"openai": LLMProviderConfig(model="gpt-4")}
            )


class TestSandboxConfig:
    """Test SandboxConfig model."""
    
    def test_valid_config(self):
        """Test valid sandbox configuration."""
        config = SandboxConfig(
            enabled=True,
            type="docker",
            cpu_limit=2.0,
            memory_limit="512m",
            timeout_seconds=60
        )
        
        assert config.enabled is True
        assert config.type == "docker"
        assert config.cpu_limit == 2.0
        assert config.memory_limit == "512m"
        assert config.timeout_seconds == 60
        assert config.network_disabled is True  # default


class TestAlphaEvolveConfig:
    """Test main AlphaEvolveConfig model."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = AlphaEvolveConfig()
        
        assert config.project_name == "AlphaEvolve"
        assert config.environment == "development"
        assert config.debug is False
        assert config.llm.default_provider == "mock"
        assert config.sandbox.enabled is True
        assert config.sandbox.type == "docker"
    
    def test_nested_config(self):
        """Test nested configuration access."""
        config = AlphaEvolveConfig(
            llm={
                "default_provider": "openai",
                "providers": {
                    "openai": {"model": "gpt-4", "temperature": 0.1}
                }
            },
            sandbox={
                "enabled": False,
                "type": "process"
            }
        )
        
        assert config.llm.default_provider == "openai"
        assert config.llm.providers["openai"].model == "gpt-4"
        assert config.llm.providers["openai"].temperature == 0.1
        assert config.sandbox.enabled is False
        assert config.sandbox.type == "process"


class TestConfigManager:
    """Test ConfigManager functionality."""
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        manager = ConfigManager()
        
        assert manager.config is not None
        assert isinstance(manager.config, AlphaEvolveConfig)
        assert manager.config.project_name == "AlphaEvolve"
    
    def test_load_yaml_config(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "project_name": "Test Project",
            "debug": True,
            "llm": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.5
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigManager(config_file)
            
            assert manager.config.project_name == "Test Project"
            assert manager.config.debug is True
            assert manager.config.llm.default_provider == "openai"
            assert manager.config.llm.providers["openai"].model == "gpt-3.5-turbo"
            assert manager.config.llm.providers["openai"].temperature == 0.5
        finally:
            os.unlink(config_file)
    
    def test_load_json_config(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "project_name": "JSON Project",
            "sandbox": {
                "enabled": False,
                "type": "process"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigManager(config_file)
            
            assert manager.config.project_name == "JSON Project"
            assert manager.config.sandbox.enabled is False
            assert manager.config.sandbox.type == "process"
        finally:
            os.unlink(config_file)
    
    def test_environment_variables(self):
        """Test loading configuration from environment variables."""
        env_vars = {
            'ALPHAEVOLVE_PROJECT_NAME': 'Env Project',
            'ALPHAEVOLVE_DEBUG': 'true',
            'ALPHAEVOLVE_LLM__DEFAULT_PROVIDER': 'mock',
            'ALPHAEVOLVE_SANDBOX__ENABLED': 'false'
        }
        
        with patch.dict(os.environ, env_vars):
            manager = ConfigManager()
            
            assert manager.config.project_name == "Env Project"
            assert manager.config.debug is True
            assert manager.config.llm.default_provider == "mock"
            assert manager.config.sandbox.enabled is False
    
    def test_config_file_not_found(self):
        """Test handling of missing configuration file."""
        manager = ConfigManager("/nonexistent/config.yaml")
        
        # Should fall back to default configuration
        assert manager.config is not None
        assert manager.config.project_name == "AlphaEvolve"
    
    def test_get_with_dot_notation(self):
        """Test getting configuration values with dot notation."""
        manager = ConfigManager()
        
        # Test existing keys
        assert manager.get('project_name') == "AlphaEvolve"
        assert manager.get('llm.default_provider') == "mock"
        assert manager.get('sandbox.enabled') is True
        
        # Test non-existent keys
        assert manager.get('nonexistent') is None
        assert manager.get('nonexistent', 'default') == 'default'
        assert manager.get('llm.nonexistent') is None
    
    def test_get_credentials(self):
        """Test getting credentials for providers."""
        config_data = {
            "llm": {
                "providers": {
                    "openai": {
                        "api_key": "test-openai-key",
                        "model": "gpt-4"
                    },
                    "anthropic": {
                        "api_key": "test-anthropic-key",
                        "model": "claude-3-sonnet-20240229",
                        "base_url": "https://custom.anthropic.com"
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigManager(config_file)
            
            openai_creds = manager.get_credentials('openai')
            assert openai_creds['api_key'] == "test-openai-key"
            assert 'base_url' not in openai_creds  # None values removed
            
            anthropic_creds = manager.get_credentials('anthropic')
            assert anthropic_creds['api_key'] == "test-anthropic-key"
            assert anthropic_creds['base_url'] == "https://custom.anthropic.com"
            
            # Non-existent provider
            unknown_creds = manager.get_credentials('unknown')
            assert unknown_creds == {}
        finally:
            os.unlink(config_file)
    
    def test_validation(self):
        """Test configuration validation."""
        # Valid configuration
        manager = ConfigManager()
        errors = manager.validate()
        assert len(errors) == 0
        
        # Invalid configuration - provider without API key
        config_data = {
            "llm": {
                "default_provider": "openai",
                "providers": {
                    "openai": {
                        "model": "gpt-4"
                        # Missing api_key
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigManager(config_file)
            errors = manager.validate()
            assert len(errors) > 0
            # Check for missing API key validation
            assert any("api key" in error.lower() for error in errors)
        finally:
            os.unlink(config_file)
    
    def test_save_to_file(self):
        """Test saving configuration to file."""
        manager = ConfigManager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            output_file = f.name
        
        try:
            manager.save_to_file(output_file)
            
            # Verify file was created and contains valid YAML
            assert os.path.exists(output_file)
            with open(output_file, 'r') as f:
                saved_config = yaml.safe_load(f)
            
            assert saved_config['project_name'] == "AlphaEvolve"
            assert 'llm' in saved_config
            assert 'sandbox' in saved_config
            
            # Verify sensitive data is redacted
            if 'providers' in saved_config.get('llm', {}):
                for provider in saved_config['llm']['providers'].values():
                    if 'api_key' in provider and provider['api_key']:
                        assert provider['api_key'] == "***REDACTED***"
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)


class TestGlobalFunctions:
    """Test global configuration functions."""
    
    def test_get_config_manager(self):
        """Test get_config_manager function."""
        # Clear global manager
        import alpha_evolve.config
        alpha_evolve.config._config_manager = None
        
        manager1 = get_config_manager()
        manager2 = get_config_manager()
        
        # Should return same instance
        assert manager1 is manager2
        
        # Should create new instance with different config file
        manager3 = get_config_manager("/different/config.yaml")
        assert manager3 is not manager1
    
    def test_get_config(self):
        """Test get_config function."""
        config = get_config()
        
        assert isinstance(config, AlphaEvolveConfig)
        assert config.project_name == "AlphaEvolve"
    
    def test_reload_config(self):
        """Test reload_config function."""
        # Create a config file
        config_data = {"project_name": "Reloaded Project"}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            reload_config(config_file)
            config = get_config()
            
            assert config.project_name == "Reloaded Project"
        finally:
            os.unlink(config_file)


class TestConfigIntegration:
    """Test configuration integration with other components."""
    
    def test_llm_interface_uses_config(self):
        """Test that LLMInterface uses configuration."""
        from alpha_evolve.llm_interface import LLMInterface
        
        # Create config with specific provider settings
        config_data = {
            "llm": {
                "default_provider": "mock",
                "providers": {
                    "mock": {
                        "model": "test-model",
                        "rate_limit_rpm": 120
                    }
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            reload_config(config_file)
            interface = LLMInterface()
            
            assert 'mock' in interface.providers
            assert interface.default_provider == 'mock'
            
            # Check rate limiting configuration
            mock_rate_limiter = interface.rate_limiters.get('mock')
            if mock_rate_limiter:
                assert mock_rate_limiter.calls_per_minute == 120
        finally:
            os.unlink(config_file)
    
    def test_evaluation_engine_uses_config(self):
        """Test that EvaluationEngine uses configuration."""
        from alpha_evolve.evaluation_engine import EvaluationEngine
        
        # Create config with specific sandbox settings
        config_data = {
            "sandbox": {
                "enabled": False,
                "type": "process",
                "timeout_seconds": 45
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            reload_config(config_file)
            engine = EvaluationEngine()
            
            assert engine.use_sandbox is False
            assert engine.sandbox_type == "process"
            assert engine.resource_limits.timeout_seconds == 45
        finally:
            os.unlink(config_file)