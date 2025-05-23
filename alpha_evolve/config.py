"""
Configuration management system for AlphaEvolve.

This module provides a comprehensive configuration system with schema validation,
environment variable support, and secure credential management.
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import yaml
import json
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from pydantic_settings import BaseSettings


class LLMProviderConfig(BaseModel):
    """Configuration for a specific LLM provider."""
    
    model_config = ConfigDict(extra='allow')
    
    api_key: Optional[str] = Field(None, description="API key for the provider")
    base_url: Optional[str] = Field(None, description="Custom base URL for the provider")
    model: str = Field(..., description="Model name to use")
    temperature: float = Field(0.2, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(2000, gt=0, description="Maximum tokens to generate")
    timeout_seconds: int = Field(30, gt=0, description="Request timeout in seconds")
    rate_limit_rpm: int = Field(60, gt=0, description="Rate limit requests per minute")


class LLMConfig(BaseModel):
    """Configuration for LLM providers and settings."""
    
    default_provider: str = Field("mock", description="Default LLM provider to use")
    fallback_provider: str = Field("mock", description="Fallback provider if default fails")
    
    providers: Dict[str, LLMProviderConfig] = Field(
        default_factory=dict,
        description="Configuration for each LLM provider"
    )
    
    @field_validator('providers')
    @classmethod
    def validate_providers(cls, v):
        """Validate provider configurations."""
        if not v:
            return v
        
        valid_providers = ['openai', 'anthropic', 'vertex_ai', 'gemini', 'mock']
        for name, config in v.items():
            if name not in valid_providers:
                raise ValueError(f"Unknown provider: {name}. Valid providers: {valid_providers}")
        
        return v
    
    @model_validator(mode='after')
    def validate_provider_references(self):
        """Ensure default and fallback providers exist in providers dict."""
        if self.default_provider and self.default_provider not in self.providers and self.default_provider != 'mock':
            raise ValueError(f"Default provider '{self.default_provider}' not found in providers")
        if self.fallback_provider and self.fallback_provider not in self.providers and self.fallback_provider != 'mock':
            raise ValueError(f"Fallback provider '{self.fallback_provider}' not found in providers")
        
        return self


class SandboxConfig(BaseModel):
    """Configuration for code execution sandboxing."""
    
    enabled: bool = Field(True, description="Whether to use sandboxing")
    type: str = Field("docker", description="Sandbox type: 'docker' or 'process'")
    
    # Resource limits
    cpu_limit: float = Field(1.0, gt=0, description="CPU limit in cores")
    memory_limit: str = Field("256m", description="Memory limit (e.g., '256m', '1g')")
    timeout_seconds: int = Field(30, gt=0, description="Execution timeout in seconds")
    max_output_size: int = Field(1024 * 1024, gt=0, description="Maximum output size in bytes")
    network_disabled: bool = Field(True, description="Disable network access in sandbox")
    
    # Docker-specific settings
    docker_image: str = Field("alphaevolve-sandbox:latest", description="Docker image to use")
    docker_pull_policy: str = Field("if_not_present", description="Docker image pull policy")


class DatabaseConfig(BaseModel):
    """Configuration for program database storage."""
    
    type: str = Field("memory", description="Database type: 'memory', 'sqlite', 'postgresql'")
    connection_string: Optional[str] = Field(None, description="Database connection string")
    
    # MAP-Elites archive settings
    feature_dimensions: List[str] = Field(
        default=["complexity", "performance"],
        description="Feature dimensions for MAP-Elites"
    )
    feature_bins: int = Field(10, gt=0, description="Number of bins per feature dimension")
    
    # Performance settings
    batch_size: int = Field(100, gt=0, description="Batch size for database operations")
    connection_pool_size: int = Field(5, gt=0, description="Database connection pool size")
    
    # Persistence settings
    checkpoint_interval: int = Field(100, gt=0, description="Generations between checkpoints")
    auto_save: bool = Field(True, description="Automatically save program database")


class EvolutionConfig(BaseModel):
    """Configuration for the evolution process."""
    
    population_size: int = Field(100, gt=0, description="Population size per generation")
    max_generations: int = Field(1000, gt=0, description="Maximum number of generations")
    elite_ratio: float = Field(0.1, gt=0, le=1, description="Ratio of elites to keep")
    
    # Selection and mutation
    selection_pressure: float = Field(2.0, gt=0, description="Selection pressure for parent selection")
    mutation_rate: float = Field(0.1, ge=0, le=1, description="Probability of mutation")
    crossover_rate: float = Field(0.8, ge=0, le=1, description="Probability of crossover")
    
    # Parallel processing
    parallel_evaluations: int = Field(4, gt=0, description="Number of parallel evaluation workers")
    batch_evaluation: bool = Field(True, description="Batch evaluations for efficiency")
    
    # Migration settings (for island model)
    migration_interval: int = Field(50, gt=0, description="Generations between migrations")
    migration_size: int = Field(5, gt=0, description="Number of individuals to migrate")


class LoggingConfig(BaseModel):
    """Configuration for logging and monitoring."""
    
    level: str = Field("INFO", description="Logging level")
    format: str = Field(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    
    # File logging
    file_enabled: bool = Field(True, description="Enable file logging")
    file_path: str = Field("alphaevolve.log", description="Log file path")
    file_max_size: str = Field("10MB", description="Maximum log file size")
    file_backup_count: int = Field(5, gt=0, description="Number of backup log files")
    
    # Console logging
    console_enabled: bool = Field(True, description="Enable console logging")
    console_level: str = Field("INFO", description="Console logging level")
    
    # Metrics and monitoring
    metrics_enabled: bool = Field(False, description="Enable metrics collection")
    metrics_port: int = Field(8000, gt=0, description="Port for metrics server")


class SecurityConfig(BaseModel):
    """Configuration for security settings."""
    
    # API key encryption
    encrypt_credentials: bool = Field(False, description="Encrypt stored credentials")
    encryption_key_path: Optional[str] = Field(None, description="Path to encryption key file")
    
    # Sandbox security
    strict_sandbox: bool = Field(True, description="Use strict sandboxing policies")
    allowed_imports: List[str] = Field(
        default_factory=lambda: ["math", "random", "json", "re", "datetime"],
        description="Allowed Python imports in sandboxed code"
    )
    blocked_functions: List[str] = Field(
        default_factory=lambda: ["exec", "eval", "compile", "__import__"],
        description="Blocked Python functions in sandboxed code"
    )
    
    # Network security
    allowed_domains: List[str] = Field(
        default_factory=list,
        description="Allowed domains for external requests"
    )


class AlphaEvolveConfig(BaseSettings):
    """Main configuration class for AlphaEvolve."""
    
    model_config = ConfigDict(
        env_prefix='ALPHAEVOLVE_',
        env_nested_delimiter='__',
        case_sensitive=False,
        extra='allow'
    )
    
    # Component configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    sandbox: SandboxConfig = Field(default_factory=SandboxConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    evolution: EvolutionConfig = Field(default_factory=EvolutionConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Global settings
    project_name: str = Field("AlphaEvolve", description="Project name")
    version: str = Field("1.0.0", description="Project version")
    environment: str = Field("development", description="Environment: development, staging, production")
    debug: bool = Field(False, description="Enable debug mode")
    
    # Paths
    config_dir: str = Field("~/.alphaevolve", description="Configuration directory")
    data_dir: str = Field("./data", description="Data directory")
    cache_dir: str = Field("./cache", description="Cache directory")


class ConfigManager:
    """Manages configuration loading, validation, and access."""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.logger = logging.getLogger(__name__)
        self._config: Optional[AlphaEvolveConfig] = None
        self._config_file = config_file
        
        # Load configuration
        self.reload()
    
    def reload(self) -> None:
        """Reload configuration from all sources."""
        try:
            # Start with default configuration
            config_data = {}
            
            # Load from file if specified
            if self._config_file:
                config_data.update(self._load_from_file(self._config_file))
            else:
                # Try to find default config files
                config_data.update(self._load_default_config_files())
            
            # Create configuration with environment variable overlay
            self._config = AlphaEvolveConfig(**config_data)
            
            # Setup directories
            self._setup_directories()
            
            self.logger.info("Configuration loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Fall back to default configuration
            self._config = AlphaEvolveConfig()
    
    def _load_from_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from a file."""
        path = Path(file_path)
        
        if not path.exists():
            self.logger.warning(f"Configuration file not found: {file_path}")
            return {}
        
        try:
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif path.suffix.lower() == '.json':
                    return json.load(f)
                else:
                    self.logger.warning(f"Unsupported config file format: {path.suffix}")
                    return {}
        except Exception as e:
            self.logger.error(f"Failed to load config file {file_path}: {e}")
            return {}
    
    def _load_default_config_files(self) -> Dict[str, Any]:
        """Load configuration from default locations."""
        config_data = {}
        
        # List of default config file locations
        default_locations = [
            "alphaevolve.yaml",
            "alphaevolve.yml", 
            "config/alphaevolve.yaml",
            "config/alphaevolve.yml",
            os.path.expanduser("~/.alphaevolve/config.yaml"),
            os.path.expanduser("~/.alphaevolve/config.yml"),
        ]
        
        for location in default_locations:
            if os.path.exists(location):
                self.logger.info(f"Loading configuration from: {location}")
                config_data.update(self._load_from_file(location))
                break
        
        return config_data
    
    def _setup_directories(self) -> None:
        """Create necessary directories."""
        if not self._config:
            return
            
        directories = [
            self._config.config_dir,
            self._config.data_dir,
            self._config.cache_dir
        ]
        
        for dir_path in directories:
            expanded_path = os.path.expanduser(dir_path)
            Path(expanded_path).mkdir(parents=True, exist_ok=True)
    
    @property
    def config(self) -> AlphaEvolveConfig:
        """Get the current configuration."""
        if self._config is None:
            self.reload()
        return self._config
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value using dot notation.
        
        Args:
            key: Configuration key (e.g., 'llm.default_provider')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        try:
            current = self.config.model_dump()
            
            for part in key.split('.'):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
            
            return current
        except Exception:
            return default
    
    def get_credentials(self, provider: str) -> Dict[str, Any]:
        """
        Get credentials for a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Dictionary containing credentials
        """
        provider_config = self.config.llm.providers.get(provider, {})
        
        if isinstance(provider_config, LLMProviderConfig):
            credentials = {
                'api_key': provider_config.api_key,
                'base_url': provider_config.base_url
            }
        else:
            credentials = {
                'api_key': provider_config.get('api_key'),
                'base_url': provider_config.get('base_url')
            }
        
        # Remove None values
        return {k: v for k, v in credentials.items() if v is not None}
    
    def validate(self) -> List[str]:
        """
        Validate the current configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Pydantic will validate when we access config
            _ = self.config
        except Exception as e:
            errors.append(str(e))
        
        # Additional custom validations
        config = self.config
        
        # Check that LLM providers have required credentials
        for name, provider_config in config.llm.providers.items():
            if isinstance(provider_config, LLMProviderConfig):
                if not provider_config.api_key and name not in ['mock']:
                    errors.append(f"LLM provider '{name}' missing API key")
        
        # Check sandbox configuration
        if config.sandbox.enabled and config.sandbox.type == 'docker':
            # Check if Docker is available (this would be a runtime check)
            pass
        
        # Check database configuration
        if config.database.type != 'memory' and not config.database.connection_string:
            errors.append("Database connection string required for non-memory databases")
        
        return errors
    
    def save_to_file(self, file_path: str) -> None:
        """
        Save current configuration to a file.
        
        Args:
            file_path: Path to save configuration
        """
        path = Path(file_path)
        
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert config to dict and remove sensitive information
        config_dict = self.config.model_dump()
        self._redact_sensitive_data(config_dict)
        
        try:
            with open(path, 'w') as f:
                if path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_dict, f, default_flow_style=False, indent=2)
                elif path.suffix.lower() == '.json':
                    json.dump(config_dict, f, indent=2)
                else:
                    raise ValueError(f"Unsupported file format: {path.suffix}")
            
            self.logger.info(f"Configuration saved to: {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration to {file_path}: {e}")
            raise
    
    def _redact_sensitive_data(self, data: Dict[str, Any]) -> None:
        """Redact sensitive information from configuration data."""
        sensitive_keys = ['api_key', 'password', 'secret', 'token', 'key']
        
        def redact_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        if value:
                            obj[key] = "***REDACTED***"
                    else:
                        redact_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    redact_recursive(item)
        
        redact_recursive(data)


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_file: Optional[str] = None) -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Args:
        config_file: Optional configuration file path
        
    Returns:
        ConfigManager instance
    """
    global _config_manager
    
    if _config_manager is None or config_file:
        _config_manager = ConfigManager(config_file)
    
    return _config_manager


def get_config() -> AlphaEvolveConfig:
    """Get the current configuration."""
    return get_config_manager().config


def reload_config(config_file: Optional[str] = None) -> None:
    """Reload configuration from sources."""
    global _config_manager
    _config_manager = ConfigManager(config_file)