"""
User-configurable feature functions and flexible feature API for MAP-Elites.

This module provides a flexible system for defining, configuring, and using
feature extraction functions in the MAP-Elites archive.
"""

from typing import Dict, List, Callable, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import logging
import inspect
from collections import defaultdict

from alpha_evolve.feature_extraction import (
    AdvancedFeatureExtractor, FeatureDescriptor, extract_code_features
)


@dataclass
class BinConfiguration:
    """
    Configuration for a single feature dimension's binning strategy.
    
    Attributes:
        strategy: Binning strategy ('uniform', 'adaptive', 'custom', 'percentile')
        num_bins: Number of bins (for uniform/adaptive strategies)
        boundaries: Custom bin boundaries (for custom strategy)
        percentiles: Percentile boundaries (for percentile strategy)
        min_value: Minimum expected value (for uniform strategy)
        max_value: Maximum expected value (for uniform strategy)
    """
    strategy: str = 'uniform'  # 'uniform', 'adaptive', 'custom', 'percentile'
    num_bins: int = 10
    boundaries: Optional[List[float]] = None
    percentiles: Optional[List[float]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        valid_strategies = ['uniform', 'adaptive', 'custom', 'percentile']
        if self.strategy not in valid_strategies:
            raise ValueError(f"Invalid strategy '{self.strategy}'. Must be one of {valid_strategies}")
        
        if self.strategy == 'custom' and not self.boundaries:
            raise ValueError("Custom strategy requires boundaries to be specified")
        
        if self.strategy == 'percentile' and not self.percentiles:
            raise ValueError("Percentile strategy requires percentiles to be specified")
        
        if self.strategy == 'uniform' and (self.min_value is None or self.max_value is None):
            raise ValueError("Uniform strategy requires min_value and max_value to be specified")


@dataclass
class FeatureConfiguration:
    """
    Configuration for a single feature in the MAP-Elites archive.
    
    Attributes:
        name: Unique name for the feature
        description: Human-readable description
        extract_fn: Function to extract this feature from code
        bin_config: Binning configuration for this feature
        weight: Weight for this feature in distance calculations
        enabled: Whether this feature is currently enabled
        validation_fn: Optional function to validate feature values
        normalization_fn: Optional function to normalize feature values
    """
    name: str
    description: str
    extract_fn: Callable[[str], float]
    bin_config: BinConfiguration
    weight: float = 1.0
    enabled: bool = True
    validation_fn: Optional[Callable[[float], bool]] = None
    normalization_fn: Optional[Callable[[float], float]] = None
    
    def extract_feature(self, code: str) -> float:
        """Extract and validate the feature value from code."""
        try:
            value = self.extract_fn(code)
            
            # Apply validation if provided
            if self.validation_fn and not self.validation_fn(value):
                raise ValueError(f"Feature '{self.name}' validation failed for value {value}")
            
            # Apply normalization if provided
            if self.normalization_fn:
                value = self.normalization_fn(value)
            
            return value
            
        except Exception as e:
            logging.getLogger(__name__).warning(f"Feature extraction failed for '{self.name}': {e}")
            return 0.0  # Default value on error
    
    def get_bin_boundaries(self, observed_values: Optional[List[float]] = None) -> List[float]:
        """
        Get bin boundaries for this feature based on its configuration.
        
        Args:
            observed_values: Optional list of observed values for adaptive/percentile binning
            
        Returns:
            List of bin boundary values
        """
        if self.bin_config.strategy == 'uniform':
            return self._get_uniform_boundaries()
        elif self.bin_config.strategy == 'custom':
            return self.bin_config.boundaries.copy()
        elif self.bin_config.strategy == 'adaptive':
            return self._get_adaptive_boundaries(observed_values or [])
        elif self.bin_config.strategy == 'percentile':
            return self._get_percentile_boundaries(observed_values or [])
        else:
            raise ValueError(f"Unknown binning strategy: {self.bin_config.strategy}")
    
    def _get_uniform_boundaries(self) -> List[float]:
        """Generate uniform bin boundaries."""
        min_val = self.bin_config.min_value
        max_val = self.bin_config.max_value
        num_bins = self.bin_config.num_bins
        
        step = (max_val - min_val) / num_bins
        return [min_val + i * step for i in range(num_bins + 1)]
    
    def _get_adaptive_boundaries(self, observed_values: List[float]) -> List[float]:
        """Generate adaptive bin boundaries based on observed values."""
        if not observed_values:
            # Fall back to uniform if no observed values
            return self._get_uniform_boundaries() if self.bin_config.min_value is not None else []
        
        sorted_values = sorted(observed_values)
        min_val = sorted_values[0]
        max_val = sorted_values[-1]
        
        if min_val == max_val:
            # All values are the same
            return [min_val - 0.5, min_val + 0.5]
        
        num_bins = self.bin_config.num_bins
        step = (max_val - min_val) / num_bins
        return [min_val + i * step for i in range(num_bins + 1)]
    
    def _get_percentile_boundaries(self, observed_values: List[float]) -> List[float]:
        """Generate percentile-based bin boundaries."""
        if not observed_values:
            return []
        
        import numpy as np
        percentiles = self.bin_config.percentiles or [0, 25, 50, 75, 100]
        return [np.percentile(observed_values, p) for p in percentiles]


class FeatureManager:
    """
    Manages a collection of configurable features for MAP-Elites.
    """
    
    def __init__(self):
        self.features: Dict[str, FeatureConfiguration] = {}
        self.feature_extractor = AdvancedFeatureExtractor()
        self.logger = logging.getLogger(__name__ + ".FeatureManager")
    
    def register_feature(self, feature_config: FeatureConfiguration) -> None:
        """Register a new feature configuration."""
        if feature_config.name in self.features:
            self.logger.warning(f"Overwriting existing feature '{feature_config.name}'")
        
        self.features[feature_config.name] = feature_config
        self.logger.info(f"Registered feature '{feature_config.name}'")
    
    def unregister_feature(self, feature_name: str) -> None:
        """Remove a feature configuration."""
        if feature_name in self.features:
            del self.features[feature_name]
            self.logger.info(f"Unregistered feature '{feature_name}'")
        else:
            self.logger.warning(f"Feature '{feature_name}' not found")
    
    def enable_feature(self, feature_name: str) -> None:
        """Enable a feature."""
        if feature_name in self.features:
            self.features[feature_name].enabled = True
            self.logger.info(f"Enabled feature '{feature_name}'")
        else:
            raise KeyError(f"Feature '{feature_name}' not found")
    
    def disable_feature(self, feature_name: str) -> None:
        """Disable a feature."""
        if feature_name in self.features:
            self.features[feature_name].enabled = False
            self.logger.info(f"Disabled feature '{feature_name}'")
        else:
            raise KeyError(f"Feature '{feature_name}' not found")
    
    def get_enabled_features(self) -> List[str]:
        """Get names of all enabled features."""
        return [name for name, config in self.features.items() if config.enabled]
    
    def extract_features(self, code: str, feature_names: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Extract features from code using configured feature functions.
        
        Args:
            code: Python source code to analyze
            feature_names: Optional list of specific features to extract.
                          If None, extracts all enabled features.
        
        Returns:
            Dictionary mapping feature names to extracted values
        """
        if feature_names is None:
            feature_names = self.get_enabled_features()
        
        results = {}
        
        for feature_name in feature_names:
            if feature_name not in self.features:
                self.logger.warning(f"Feature '{feature_name}' not found, skipping")
                continue
            
            feature_config = self.features[feature_name]
            if not feature_config.enabled:
                self.logger.debug(f"Feature '{feature_name}' is disabled, skipping")
                continue
            
            try:
                value = feature_config.extract_feature(code)
                results[feature_name] = value
            except Exception as e:
                self.logger.error(f"Failed to extract feature '{feature_name}': {e}")
                results[feature_name] = 0.0  # Default value on error
        
        return results
    
    def get_bin_boundaries_for_features(
        self, 
        feature_names: Optional[List[str]] = None,
        observed_data: Optional[Dict[str, List[float]]] = None
    ) -> Dict[str, List[float]]:
        """
        Get bin boundaries for multiple features.
        
        Args:
            feature_names: Features to get boundaries for (default: all enabled)
            observed_data: Dictionary mapping feature names to lists of observed values
        
        Returns:
            Dictionary mapping feature names to their bin boundaries
        """
        if feature_names is None:
            feature_names = self.get_enabled_features()
        
        observed_data = observed_data or {}
        boundaries = {}
        
        for feature_name in feature_names:
            if feature_name not in self.features:
                continue
            
            feature_config = self.features[feature_name]
            observed_values = observed_data.get(feature_name, [])
            
            try:
                boundaries[feature_name] = feature_config.get_bin_boundaries(observed_values)
            except Exception as e:
                self.logger.error(f"Failed to get bin boundaries for '{feature_name}': {e}")
                # Provide default boundaries
                boundaries[feature_name] = [0.0, 1.0]
        
        return boundaries
    
    def calculate_feature_distance(
        self, 
        features1: Dict[str, float], 
        features2: Dict[str, float]
    ) -> float:
        """
        Calculate weighted distance between two feature vectors.
        
        Args:
            features1: First feature vector
            features2: Second feature vector
        
        Returns:
            Weighted distance between features
        """
        common_features = set(features1.keys()) & set(features2.keys())
        
        if not common_features:
            return 1.0  # Maximum distance if no common features
        
        total_weighted_distance = 0.0
        total_weight = 0.0
        
        for feature_name in common_features:
            if feature_name not in self.features:
                continue
            
            feature_config = self.features[feature_name]
            weight = feature_config.weight
            
            val1, val2 = features1[feature_name], features2[feature_name]
            
            # Normalize distance by feature range if possible
            bin_boundaries = feature_config.get_bin_boundaries()
            if len(bin_boundaries) >= 2:
                range_size = bin_boundaries[-1] - bin_boundaries[0]
                if range_size > 0:
                    normalized_distance = abs(val1 - val2) / range_size
                else:
                    normalized_distance = 0.0 if val1 == val2 else 1.0
            else:
                normalized_distance = 0.0 if val1 == val2 else 1.0
            
            total_weighted_distance += weight * normalized_distance
            total_weight += weight
        
        # Return weighted average distance
        return total_weighted_distance / total_weight if total_weight > 0 else 0.0
    
    def get_feature_info(self, feature_name: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive information about a feature."""
        if feature_name not in self.features:
            return None
        
        config = self.features[feature_name]
        return {
            'name': config.name,
            'description': config.description,
            'enabled': config.enabled,
            'weight': config.weight,
            'binning_strategy': config.bin_config.strategy,
            'num_bins': config.bin_config.num_bins,
            'has_validation': config.validation_fn is not None,
            'has_normalization': config.normalization_fn is not None
        }
    
    def list_features(self) -> Dict[str, Dict[str, Any]]:
        """List all registered features with their information."""
        return {name: self.get_feature_info(name) for name in self.features.keys()}


class DefaultFeatureLibrary:
    """
    Library of default feature configurations based on the advanced feature extractor.
    """
    
    @staticmethod
    def create_complexity_feature() -> FeatureConfiguration:
        """Create cyclomatic complexity feature."""
        def extract_complexity(code: str) -> float:
            features = extract_code_features(code, ['cyclomatic_complexity'])
            return float(features.get('cyclomatic_complexity', 1))
        
        return FeatureConfiguration(
            name='complexity',
            description='McCabe cyclomatic complexity',
            extract_fn=extract_complexity,
            bin_config=BinConfiguration(
                strategy='uniform',
                num_bins=10,
                min_value=1.0,
                max_value=20.0
            ),
            weight=1.0
        )
    
    @staticmethod
    def create_size_feature() -> FeatureConfiguration:
        """Create code size feature based on line count."""
        def extract_size(code: str) -> float:
            features = extract_code_features(code, ['line_count'])
            return float(features.get('line_count', 1))
        
        return FeatureConfiguration(
            name='size',
            description='Number of lines of code',
            extract_fn=extract_size,
            bin_config=BinConfiguration(
                strategy='adaptive',
                num_bins=8
            ),
            weight=0.8
        )
    
    @staticmethod
    def create_quality_feature() -> FeatureConfiguration:
        """Create code quality feature based on documentation and naming."""
        def extract_quality(code: str) -> float:
            features = extract_code_features(code, ['documentation_ratio', 'naming_consistency'])
            doc_ratio = features.get('documentation_ratio', 0.0)
            naming_consistency = features.get('naming_consistency', 1.0)
            return (doc_ratio + naming_consistency) / 2.0
        
        return FeatureConfiguration(
            name='quality',
            description='Code quality based on documentation and naming',
            extract_fn=extract_quality,
            bin_config=BinConfiguration(
                strategy='uniform',
                num_bins=5,
                min_value=0.0,
                max_value=1.0
            ),
            weight=0.5
        )
    
    @staticmethod
    def create_diversity_feature() -> FeatureConfiguration:
        """Create diversity feature based on control flow and import diversity."""
        def extract_diversity(code: str) -> float:
            features = extract_code_features(code, ['control_flow_diversity', 'import_diversity'])
            control_diversity = features.get('control_flow_diversity', 0.0)
            import_diversity = features.get('import_diversity', 0.0)
            # Normalize to 0-1 range
            return min(1.0, (control_diversity + import_diversity / 10.0) / 2.0)
        
        return FeatureConfiguration(
            name='diversity',
            description='Code diversity based on control flow and imports',
            extract_fn=extract_diversity,
            bin_config=BinConfiguration(
                strategy='uniform',
                num_bins=6,
                min_value=0.0,
                max_value=1.0
            ),
            weight=0.7
        )
    
    @staticmethod
    def create_performance_feature() -> FeatureConfiguration:
        """Create performance feature (placeholder - would integrate with evaluation results)."""
        def extract_performance(code: str) -> float:
            # This is a placeholder - in a real system, this would integrate
            # with the evaluation engine to get actual performance metrics
            features = extract_code_features(code, ['cyclomatic_complexity', 'comprehension_usage'])
            complexity = features.get('cyclomatic_complexity', 1)
            comprehensions = features.get('comprehension_usage', 0)
            
            # Simple heuristic: fewer complex operations might be faster
            # More comprehensions might be more efficient
            base_performance = max(0.1, 1.0 - (complexity - 1) / 20.0)
            comprehension_bonus = min(0.3, comprehensions * 0.1)
            return min(1.0, base_performance + comprehension_bonus)
        
        return FeatureConfiguration(
            name='performance',
            description='Estimated performance based on code characteristics',
            extract_fn=extract_performance,
            bin_config=BinConfiguration(
                strategy='uniform',
                num_bins=10,
                min_value=0.0,
                max_value=1.0
            ),
            weight=1.5  # Higher weight for performance
        )
    
    @staticmethod
    def create_default_feature_manager() -> FeatureManager:
        """Create a feature manager with default feature configurations."""
        manager = FeatureManager()
        
        # Register default features
        manager.register_feature(DefaultFeatureLibrary.create_complexity_feature())
        manager.register_feature(DefaultFeatureLibrary.create_size_feature())
        manager.register_feature(DefaultFeatureLibrary.create_quality_feature())
        manager.register_feature(DefaultFeatureLibrary.create_diversity_feature())
        manager.register_feature(DefaultFeatureLibrary.create_performance_feature())
        
        return manager


def create_custom_feature(
    name: str,
    description: str,
    extract_fn: Callable[[str], float],
    binning_strategy: str = 'uniform',
    num_bins: int = 10,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None,
    weight: float = 1.0
) -> FeatureConfiguration:
    """
    Convenience function to create a custom feature configuration.
    
    Args:
        name: Feature name
        description: Feature description
        extract_fn: Function to extract feature value from code
        binning_strategy: Binning strategy ('uniform', 'adaptive', 'custom')
        num_bins: Number of bins
        min_value: Minimum value (for uniform strategy)
        max_value: Maximum value (for uniform strategy)
        weight: Feature weight in distance calculations
    
    Returns:
        Configured FeatureConfiguration instance
    """
    bin_config = BinConfiguration(
        strategy=binning_strategy,
        num_bins=num_bins,
        min_value=min_value,
        max_value=max_value
    )
    
    return FeatureConfiguration(
        name=name,
        description=description,
        extract_fn=extract_fn,
        bin_config=bin_config,
        weight=weight
    )


# Global feature manager instance
_global_feature_manager: Optional[FeatureManager] = None


def get_feature_manager() -> FeatureManager:
    """Get the global feature manager instance."""
    global _global_feature_manager
    if _global_feature_manager is None:
        _global_feature_manager = DefaultFeatureLibrary.create_default_feature_manager()
    return _global_feature_manager


def set_feature_manager(manager: FeatureManager) -> None:
    """Set the global feature manager instance."""
    global _global_feature_manager
    _global_feature_manager = manager


def extract_configured_features(code: str, feature_names: Optional[List[str]] = None) -> Dict[str, float]:
    """
    Convenience function to extract features using the global feature manager.
    
    Args:
        code: Python source code to analyze
        feature_names: Optional list of specific features to extract
    
    Returns:
        Dictionary mapping feature names to extracted values
    """
    manager = get_feature_manager()
    return manager.extract_features(code, feature_names)