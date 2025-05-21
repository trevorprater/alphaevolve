"""
Tests for the LLMInterface class.
"""

import pytest
import asyncio
from typing import Dict, Any, Optional

from alpha_evolve.llm_interface import LLMInterface


def test_init():
    """
    Test LLMInterface initialization with default and custom configurations.
    """
    # Test with default config
    interface = LLMInterface()
    assert interface.api_keys == {}
    assert "flash" in interface.model_configs
    assert "pro" in interface.model_configs
    
    # Test with custom config
    custom_api_keys = {"service1": "key1", "service2": "key2"}
    custom_model_configs = {
        "custom_model": {"model_name": "custom-model-name"},
        "pro": {"model_name": "custom-pro-model"}
    }
    
    interface = LLMInterface(
        api_keys=custom_api_keys,
        model_configs=custom_model_configs
    )
    
    assert interface.api_keys == custom_api_keys
    assert interface.model_configs == custom_model_configs


def test_generate_code_modification_flash():
    """
    Test generate_code_modification with 'flash' LLM type.
    """
    interface = LLMInterface()
    
    # Use asyncio.run to run the coroutine
    result = asyncio.run(interface.generate_code_modification(
        prompt="Test prompt", 
        llm_type="flash"
    ))
    
    # Check that the response matches the expected mock response for flash
    expected = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 3  # Mock LLM modified logic\n>>>>>>>> REPLACE"
    assert result == expected


def test_generate_code_modification_pro():
    """
    Test generate_code_modification with 'pro' LLM type.
    """
    interface = LLMInterface()
    
    # Use asyncio.run to run the coroutine
    result = asyncio.run(interface.generate_code_modification(
        prompt="Test prompt", 
        llm_type="pro"
    ))
    
    # Check that the response matches the expected mock response for pro
    expected = "<<<<<<<< SEARCH\nres += input_x * 2  # Initial logic\n========\nres += input_x * 5  # Pro model enhanced logic\n>>>>>>>> REPLACE"
    assert result == expected


def test_generate_code_modification_unknown_type():
    """
    Test generate_code_modification with an unknown LLM type.
    """
    interface = LLMInterface()
    
    # Use asyncio and pytest.raises together
    with pytest.raises(RuntimeError) as excinfo:
        asyncio.run(interface.generate_code_modification(
            prompt="Test prompt", 
            llm_type="unknown_type"
        ))
    
    # Check the error message
    assert "Error generating code modification: Unsupported LLM type: unknown_type" in str(excinfo.value)