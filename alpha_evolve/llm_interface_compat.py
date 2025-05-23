"""
Compatibility layer for transitioning from LLM interface v1 to v2.

This module provides a compatibility wrapper that allows existing code
to work with the new v2 interface while gradually migrating.
"""
import logging
from typing import Optional, Dict, Any, List, Union

from alpha_evolve.llm_interface_v2 import (
    LLMInterface as LLMInterfaceV2,
    LLMResponse
)


class LLMInterfaceCompat:
    """
    Compatibility wrapper for LLM interface that supports both v1 and v2 usage patterns.
    """
    
    def __init__(self, use_v2: bool = True):
        """
        Initialize compatibility interface.
        
        Args:
            use_v2: Whether to use v2 interface (True) or import v1 (False)
        """
        self.use_v2 = use_v2
        self.logger = logging.getLogger(__name__)
        
        if use_v2:
            self.interface = LLMInterfaceV2()
        else:
            # Fall back to v1 if explicitly requested
            from alpha_evolve.llm_interface import LLMInterface as LLMInterfaceV1
            self.interface = LLMInterfaceV1()
            
    async def generate_code_modification(
        self,
        prompt: str,
        llm_type: str = "flash",
        provider: Optional[str] = None,
        **kwargs
    ) -> Union[str, LLMResponse]:
        """
        Generate code modification with backward compatibility.
        
        Supports both v1 style (llm_type) and v2 style (provider) parameters.
        
        Args:
            prompt: The prompt for code generation
            llm_type: Legacy parameter for v1 compatibility ('flash' or 'pro')
            provider: v2 style provider specification
            **kwargs: Additional parameters
            
        Returns:
            String for v1 compatibility or LLMResponse for v2
        """
        if self.use_v2:
            # Map llm_type to appropriate v2 parameters if provider not specified
            if not provider and llm_type:
                if llm_type == "pro":
                    # Use more powerful models for "pro" requests
                    if "anthropic" in self.interface.get_available_providers():
                        provider = "anthropic"
                        kwargs.setdefault('model', 'claude-3-sonnet-20240229')
                    elif "openai" in self.interface.get_available_providers():
                        provider = "openai"
                        kwargs.setdefault('model', 'gpt-4')
                else:  # flash
                    # Use faster/cheaper models for "flash" requests
                    if "openai" in self.interface.get_available_providers():
                        provider = "openai"
                        kwargs.setdefault('model', 'gpt-3.5-turbo')
                    elif "gemini" in self.interface.get_available_providers():
                        provider = "gemini"
                        kwargs.setdefault('model', 'gemini-pro')
                        
            # Call v2 interface
            response = await self.interface.generate_code_modification(
                prompt=prompt,
                provider=provider,
                **kwargs
            )
            
            # Return based on caller expectation
            if kwargs.get('return_response_object', True):
                return response
            else:
                # Return string for backward compatibility
                return response.content
        else:
            # Use v1 interface
            return await self.interface.generate_code_modification(
                prompt=prompt,
                llm_type=llm_type,
                provider=provider,
                **kwargs
            )
            
    async def critique_code(
        self,
        code: str,
        criteria: str = "correctness, performance, readability",
        provider: Optional[str] = None,
        **kwargs
    ) -> Union[str, LLMResponse]:
        """
        Critique code with backward compatibility.
        
        Args:
            code: Code to critique
            criteria: Evaluation criteria
            provider: Provider to use
            **kwargs: Additional parameters
            
        Returns:
            String for v1 compatibility or LLMResponse for v2
        """
        if self.use_v2:
            response = await self.interface.critique_code(
                code=code,
                criteria=criteria,
                provider=provider,
                **kwargs
            )
            
            # Return based on caller expectation
            if kwargs.get('return_response_object', True):
                return response
            else:
                return response.content
        else:
            return await self.interface.critique_code(
                code=code,
                criteria=criteria,
                provider=provider
            )
            
    def get_available_providers(self) -> List[str]:
        """Get list of available providers."""
        return self.interface.get_available_providers()
        
    def get_default_provider(self) -> Optional[str]:
        """Get default provider name."""
        return self.interface.get_default_provider()
        
    def register_provider(self, name: str, provider: Any, default: bool = False):
        """Register a provider (v1 compatibility)."""
        if hasattr(self.interface, 'register_provider'):
            self.interface.register_provider(name, provider, default)
        else:
            self.logger.warning("Provider registration not supported in v2 through compat layer")


# Convenience function for drop-in replacement
def create_llm_interface(use_v2: bool = True) -> LLMInterfaceCompat:
    """
    Create an LLM interface with compatibility support.
    
    Args:
        use_v2: Whether to use v2 (recommended) or v1
        
    Returns:
        LLMInterfaceCompat instance
    """
    return LLMInterfaceCompat(use_v2=use_v2)


# Example migration helper
async def migrate_llm_call(old_code_example: str):
    """
    Example showing how to migrate from v1 to v2.
    """
    # Old v1 style
    llm_v1 = create_llm_interface(use_v2=False)
    result_v1 = await llm_v1.generate_code_modification(
        "Optimize this function",
        llm_type="pro"
    )
    print(f"V1 Result: {result_v1}")
    
    # New v2 style with compatibility
    llm_compat = create_llm_interface(use_v2=True)
    
    # Can still use old style
    result_compat = await llm_compat.generate_code_modification(
        "Optimize this function",
        llm_type="pro",
        return_response_object=False  # Get string like v1
    )
    print(f"Compat Result: {result_compat}")
    
    # Or use new style
    response_v2 = await llm_compat.generate_code_modification(
        "Optimize this function",
        provider="anthropic",
        use_thinking=True
    )
    print(f"V2 Response: {response_v2.content}")
    print(f"Used provider: {response_v2.provider}")
    print(f"Cost: ${response_v2.cost:.4f}")