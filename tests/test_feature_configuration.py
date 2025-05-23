"""
Tests for the configurable feature system.
"""

import pytest
import numpy as np
from alpha_evolve.feature_configuration import (
    BinConfiguration, FeatureConfiguration, FeatureManager,
    DefaultFeatureLibrary, create_custom_feature, get_feature_manager,
    set_feature_manager, extract_configured_features
)


class TestBinConfiguration:
    """Test bin configuration functionality."""
    
    def test_uniform_bin_config(self):
        """Test uniform binning configuration."""
        config = BinConfiguration(
            strategy='uniform',
            num_bins=5,
            min_value=0.0,
            max_value=10.0
        )
        
        assert config.strategy == 'uniform'
        assert config.num_bins == 5
        assert config.min_value == 0.0
        assert config.max_value == 10.0
    
    def test_custom_bin_config(self):
        """Test custom binning configuration."""
        boundaries = [0, 2, 5, 10, 20]
        config = BinConfiguration(
            strategy='custom',
            boundaries=boundaries
        )
        
        assert config.strategy == 'custom'
        assert config.boundaries == boundaries
    
    def test_percentile_bin_config(self):
        """Test percentile binning configuration."""
        percentiles = [0, 25, 50, 75, 100]
        config = BinConfiguration(
            strategy='percentile',
            percentiles=percentiles
        )
        
        assert config.strategy == 'percentile'
        assert config.percentiles == percentiles
    
    def test_invalid_strategy(self):
        """Test validation of invalid strategy."""
        with pytest.raises(ValueError, match="Invalid strategy"):
            BinConfiguration(strategy='invalid_strategy')
    
    def test_custom_without_boundaries(self):
        """Test custom strategy without boundaries raises error."""
        with pytest.raises(ValueError, match="Custom strategy requires boundaries"):
            BinConfiguration(strategy='custom')
    
    def test_percentile_without_percentiles(self):
        """Test percentile strategy without percentiles raises error."""
        with pytest.raises(ValueError, match="Percentile strategy requires percentiles"):
            BinConfiguration(strategy='percentile')
    
    def test_uniform_without_range(self):
        """Test uniform strategy without min/max values raises error."""
        with pytest.raises(ValueError, match="Uniform strategy requires min_value and max_value"):
            BinConfiguration(strategy='uniform', num_bins=5)


class TestFeatureConfiguration:
    """Test feature configuration functionality."""
    
    def test_basic_feature_config(self):
        """Test basic feature configuration."""
        def extract_fn(code: str) -> float:
            return len(code.split('\n'))
        
        bin_config = BinConfiguration(strategy='uniform', num_bins=5, min_value=1.0, max_value=100.0)
        
        feature = FeatureConfiguration(
            name='line_count',
            description='Number of lines',
            extract_fn=extract_fn,
            bin_config=bin_config,
            weight=1.0
        )
        
        assert feature.name == 'line_count'
        assert feature.description == 'Number of lines'
        assert feature.weight == 1.0
        assert feature.enabled is True
    
    def test_feature_extraction(self):
        """Test feature value extraction."""
        def extract_fn(code: str) -> float:
            return len(code.split('\n'))
        
        bin_config = BinConfiguration(strategy='uniform', num_bins=5, min_value=1.0, max_value=100.0)
        feature = FeatureConfiguration(
            name='line_count',
            description='Number of lines',
            extract_fn=extract_fn,
            bin_config=bin_config
        )
        
        code = "def hello():\n    print('world')\n    return True"
        value = feature.extract_feature(code)
        assert value == 3.0  # Three lines
    
    def test_feature_validation(self):
        """Test feature validation."""
        def extract_fn(code: str) -> float:
            return len(code)
        
        def validation_fn(value: float) -> bool:
            return value > 0
        
        bin_config = BinConfiguration(strategy='uniform', num_bins=5, min_value=1.0, max_value=100.0)
        feature = FeatureConfiguration(
            name='char_count',
            description='Character count',
            extract_fn=extract_fn,
            bin_config=bin_config,
            validation_fn=validation_fn
        )
        
        # Valid code
        valid_code = "print('hello')"
        value = feature.extract_feature(valid_code)
        assert value > 0
        
        # Invalid case (empty code)
        empty_code = ""
        value = feature.extract_feature(empty_code)
        assert value == 0.0  # Default value on validation failure
    
    def test_feature_normalization(self):
        """Test feature normalization."""
        def extract_fn(code: str) -> float:
            return len(code)
        
        def normalization_fn(value: float) -> float:
            return value / 100.0  # Normalize to 0-1 range
        
        bin_config = BinConfiguration(strategy='uniform', num_bins=5, min_value=0.0, max_value=1.0)
        feature = FeatureConfiguration(
            name='normalized_length',
            description='Normalized code length',
            extract_fn=extract_fn,
            bin_config=bin_config,
            normalization_fn=normalization_fn
        )
        
        code = "print('hello')"  # 14 characters
        value = feature.extract_feature(code)
        assert value == 0.14  # 14/100
    
    def test_uniform_bin_boundaries(self):
        """Test uniform bin boundary generation."""
        bin_config = BinConfiguration(strategy='uniform', num_bins=4, min_value=0.0, max_value=10.0)
        feature = FeatureConfiguration(
            name='test',
            description='Test feature',
            extract_fn=lambda x: 1.0,
            bin_config=bin_config
        )
        
        boundaries = feature.get_bin_boundaries()
        expected = [0.0, 2.5, 5.0, 7.5, 10.0]
        assert boundaries == expected
    
    def test_custom_bin_boundaries(self):
        """Test custom bin boundaries."""
        custom_boundaries = [0, 1, 5, 10, 50]
        bin_config = BinConfiguration(strategy='custom', boundaries=custom_boundaries)
        feature = FeatureConfiguration(
            name='test',
            description='Test feature',
            extract_fn=lambda x: 1.0,
            bin_config=bin_config
        )
        
        boundaries = feature.get_bin_boundaries()
        assert boundaries == custom_boundaries
    
    def test_adaptive_bin_boundaries(self):
        """Test adaptive bin boundaries."""
        bin_config = BinConfiguration(strategy='adaptive', num_bins=3)
        feature = FeatureConfiguration(
            name='test',
            description='Test feature',
            extract_fn=lambda x: 1.0,
            bin_config=bin_config
        )
        
        observed_values = [1.0, 2.0, 3.0, 4.0, 5.0]
        boundaries = feature.get_bin_boundaries(observed_values)
        
        # Should create 3 bins from 1.0 to 5.0
        expected_step = (5.0 - 1.0) / 3
        expected = [1.0, 1.0 + expected_step, 1.0 + 2*expected_step, 5.0]
        
        assert len(boundaries) == 4
        assert boundaries[0] == 1.0
        assert boundaries[-1] == 5.0


class TestFeatureManager:
    """Test feature manager functionality."""
    
    def test_feature_registration(self):
        """Test feature registration and management."""
        manager = FeatureManager()
        
        # Create a simple feature
        def extract_fn(code: str) -> float:
            return len(code.split('\n'))
        
        bin_config = BinConfiguration(strategy='uniform', num_bins=5, min_value=1.0, max_value=100.0)
        feature = FeatureConfiguration(
            name='line_count',
            description='Number of lines',
            extract_fn=extract_fn,
            bin_config=bin_config
        )
        
        # Register feature
        manager.register_feature(feature)
        assert 'line_count' in manager.features
        assert manager.get_enabled_features() == ['line_count']
        
        # Disable feature
        manager.disable_feature('line_count')
        assert manager.get_enabled_features() == []
        
        # Enable feature
        manager.enable_feature('line_count')
        assert manager.get_enabled_features() == ['line_count']
        
        # Unregister feature
        manager.unregister_feature('line_count')
        assert 'line_count' not in manager.features
    
    def test_feature_extraction_with_manager(self):
        """Test feature extraction through manager."""
        manager = FeatureManager()
        
        # Register multiple features
        def line_count(code: str) -> float:
            return len(code.split('\n'))
        
        def char_count(code: str) -> float:
            return len(code)
        
        line_feature = FeatureConfiguration(
            name='lines',
            description='Line count',
            extract_fn=line_count,
            bin_config=BinConfiguration(strategy='uniform', num_bins=5, min_value=1.0, max_value=100.0)
        )
        
        char_feature = FeatureConfiguration(
            name='chars',
            description='Character count',
            extract_fn=char_count,
            bin_config=BinConfiguration(strategy='uniform', num_bins=5, min_value=1.0, max_value=1000.0)
        )
        
        manager.register_feature(line_feature)
        manager.register_feature(char_feature)
        
        # Extract features
        code = "def hello():\n    print('world')"
        features = manager.extract_features(code)
        
        assert 'lines' in features
        assert 'chars' in features
        assert features['lines'] == 2.0  # Two lines
        assert features['chars'] > 0  # Some characters
    
    def test_bin_boundaries_for_features(self):
        """Test getting bin boundaries for multiple features."""
        manager = FeatureManager()
        
        # Register a feature with uniform binning
        def extract_fn(code: str) -> float:
            return 1.0
        
        feature = FeatureConfiguration(
            name='test_feature',
            description='Test',
            extract_fn=extract_fn,
            bin_config=BinConfiguration(strategy='uniform', num_bins=3, min_value=0.0, max_value=6.0)
        )
        
        manager.register_feature(feature)
        
        boundaries = manager.get_bin_boundaries_for_features(['test_feature'])
        
        assert 'test_feature' in boundaries
        assert boundaries['test_feature'] == [0.0, 2.0, 4.0, 6.0]
    
    def test_feature_distance_calculation(self):
        """Test distance calculation between feature vectors."""
        manager = FeatureManager()
        
        # Register a simple feature
        def extract_fn(code: str) -> float:
            return 1.0
        
        feature = FeatureConfiguration(
            name='test',
            description='Test',
            extract_fn=extract_fn,
            bin_config=BinConfiguration(strategy='uniform', num_bins=10, min_value=0.0, max_value=10.0),
            weight=1.0
        )
        
        manager.register_feature(feature)
        
        # Test distance calculation
        features1 = {'test': 2.0}
        features2 = {'test': 4.0}
        
        distance = manager.calculate_feature_distance(features1, features2)
        
        # Distance should be normalized: |2-4| / (10-0) = 2/10 = 0.2
        assert abs(distance - 0.2) < 1e-6
    
    def test_feature_info(self):
        """Test getting feature information."""
        manager = FeatureManager()
        
        def extract_fn(code: str) -> float:
            return 1.0
        
        feature = FeatureConfiguration(
            name='test_feature',
            description='A test feature',
            extract_fn=extract_fn,
            bin_config=BinConfiguration(strategy='uniform', num_bins=5, min_value=0.0, max_value=10.0),
            weight=1.5
        )
        
        manager.register_feature(feature)
        
        info = manager.get_feature_info('test_feature')
        
        assert info['name'] == 'test_feature'
        assert info['description'] == 'A test feature'
        assert info['enabled'] is True
        assert info['weight'] == 1.5
        assert info['binning_strategy'] == 'uniform'
        assert info['num_bins'] == 5
    
    def test_list_features(self):
        """Test listing all features."""
        manager = FeatureManager()
        
        # Register multiple features
        for i in range(3):
            feature = FeatureConfiguration(
                name=f'feature_{i}',
                description=f'Feature {i}',
                extract_fn=lambda x: float(i),
                bin_config=BinConfiguration(strategy='uniform', num_bins=5, min_value=0.0, max_value=10.0)
            )
            manager.register_feature(feature)
        
        features_list = manager.list_features()
        
        assert len(features_list) == 3
        for i in range(3):
            assert f'feature_{i}' in features_list
            assert features_list[f'feature_{i}']['description'] == f'Feature {i}'


class TestDefaultFeatureLibrary:
    """Test default feature library."""
    
    def test_create_complexity_feature(self):
        """Test complexity feature creation."""
        feature = DefaultFeatureLibrary.create_complexity_feature()
        
        assert feature.name == 'complexity'
        assert 'complexity' in feature.description.lower()
        assert feature.bin_config.strategy == 'uniform'
        
        # Test extraction
        simple_code = "print('hello')"
        complex_code = """
def complex_function(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                print(i)
    else:
        return 0
    return 1
"""
        
        simple_value = feature.extract_feature(simple_code)
        complex_value = feature.extract_feature(complex_code)
        
        assert complex_value > simple_value  # More complex code should have higher complexity
    
    def test_create_size_feature(self):
        """Test size feature creation."""
        feature = DefaultFeatureLibrary.create_size_feature()
        
        assert feature.name == 'size'
        assert feature.bin_config.strategy == 'adaptive'
        
        # Test extraction
        short_code = "x = 1"
        long_code = "\n".join([f"line_{i} = {i}" for i in range(10)])
        
        short_value = feature.extract_feature(short_code)
        long_value = feature.extract_feature(long_code)
        
        assert long_value > short_value  # Longer code should have higher size
    
    def test_create_quality_feature(self):
        """Test quality feature creation."""
        feature = DefaultFeatureLibrary.create_quality_feature()
        
        assert feature.name == 'quality'
        assert feature.bin_config.min_value == 0.0
        assert feature.bin_config.max_value == 1.0
        
        # Test extraction
        poor_quality_code = "def f(x):return x*2"  # No docstring, poor naming
        good_quality_code = """
def calculate_double(input_value):
    '''Calculate double of the input value.'''
    return input_value * 2
"""
        
        poor_value = feature.extract_feature(poor_quality_code)
        good_value = feature.extract_feature(good_quality_code)
        
        assert good_value >= poor_value  # Better quality code should have higher score
    
    def test_create_default_feature_manager(self):
        """Test default feature manager creation."""
        manager = DefaultFeatureLibrary.create_default_feature_manager()
        
        # Should have multiple default features
        enabled_features = manager.get_enabled_features()
        assert len(enabled_features) >= 4  # At least complexity, size, quality, diversity, performance
        
        # Check that all features can extract values
        test_code = """
def fibonacci(n):
    '''Calculate fibonacci number.'''
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""
        
        features = manager.extract_features(test_code)
        
        assert len(features) == len(enabled_features)
        for feature_name, value in features.items():
            assert isinstance(value, (int, float))
            assert not np.isnan(value)


class TestCustomFeatures:
    """Test custom feature creation utilities."""
    
    def test_create_custom_feature(self):
        """Test custom feature creation function."""
        def word_count(code: str) -> float:
            return len(code.split())
        
        feature = create_custom_feature(
            name='word_count',
            description='Number of words in code',
            extract_fn=word_count,
            binning_strategy='uniform',
            num_bins=8,
            min_value=1.0,
            max_value=100.0,
            weight=0.5
        )
        
        assert feature.name == 'word_count'
        assert feature.description == 'Number of words in code'
        assert feature.weight == 0.5
        assert feature.bin_config.strategy == 'uniform'
        assert feature.bin_config.num_bins == 8
        
        # Test extraction
        code = "def hello world function(): pass"
        value = feature.extract_feature(code)
        assert value == 5.0  # 5 words


class TestGlobalFeatureManager:
    """Test global feature manager functionality."""
    
    def test_get_feature_manager(self):
        """Test getting global feature manager."""
        manager1 = get_feature_manager()
        manager2 = get_feature_manager()
        
        # Should return the same instance
        assert manager1 is manager2
        
        # Should have default features
        assert len(manager1.get_enabled_features()) > 0
    
    def test_set_feature_manager(self):
        """Test setting global feature manager."""
        # Create custom manager
        custom_manager = FeatureManager()
        
        # Set as global
        set_feature_manager(custom_manager)
        
        # Should now return the custom manager
        retrieved_manager = get_feature_manager()
        assert retrieved_manager is custom_manager
        
        # Reset to default
        set_feature_manager(DefaultFeatureLibrary.create_default_feature_manager())
    
    def test_extract_configured_features(self):
        """Test convenience function for feature extraction."""
        code = "def test(): pass"
        features = extract_configured_features(code)
        
        assert isinstance(features, dict)
        assert len(features) > 0
        
        # Test with specific features
        specific_features = extract_configured_features(code, ['complexity'])
        assert 'complexity' in specific_features
        assert len(specific_features) == 1


class TestIntegrationScenarios:
    """Test realistic integration scenarios."""
    
    def test_evolutionary_workflow(self):
        """Test a realistic evolutionary workflow with features."""
        # Create manager with custom features
        manager = FeatureManager()
        
        # Add features relevant for code evolution
        complexity_feature = DefaultFeatureLibrary.create_complexity_feature()
        size_feature = DefaultFeatureLibrary.create_size_feature()
        
        manager.register_feature(complexity_feature)
        manager.register_feature(size_feature)
        
        # Simulate population of code variants
        code_variants = [
            "def sort(lst): return sorted(lst)",
            "def sort(lst): return lst.sort() or lst",
            """
def sort(lst):
    for i in range(len(lst)):
        for j in range(i+1, len(lst)):
            if lst[i] > lst[j]:
                lst[i], lst[j] = lst[j], lst[i]
    return lst
""",
            """
def sort(lst):
    '''Bubble sort implementation.'''
    n = len(lst)
    for i in range(n):
        swapped = False
        for j in range(0, n-i-1):
            if lst[j] > lst[j+1]:
                lst[j], lst[j+1] = lst[j+1], lst[j]
                swapped = True
        if not swapped:
            break
    return lst
"""
        ]
        
        # Extract features for all variants
        population_features = []
        for code in code_variants:
            features = manager.extract_features(code)
            population_features.append(features)
        
        # All variants should have feature values
        assert len(population_features) == len(code_variants)
        
        # Calculate distances between variants
        distances = []
        for i in range(len(population_features)):
            for j in range(i+1, len(population_features)):
                distance = manager.calculate_feature_distance(
                    population_features[i], population_features[j]
                )
                distances.append(distance)
        
        # Should have calculated distances
        assert len(distances) == 6  # 4 choose 2 = 6 pairs
        assert all(0.0 <= d <= 1.0 for d in distances)  # All distances in valid range
        
        # Get bin boundaries for archive
        observed_data = {
            'complexity': [f['complexity'] for f in population_features],
            'size': [f['size'] for f in population_features]
        }
        
        boundaries = manager.get_bin_boundaries_for_features(observed_data=observed_data)
        
        assert 'complexity' in boundaries
        assert 'size' in boundaries
        assert len(boundaries['complexity']) > 1
        assert len(boundaries['size']) > 1
    
    def test_feature_configuration_persistence(self):
        """Test that feature configurations work consistently."""
        # Create manager with specific configuration
        manager = FeatureManager()
        
        # Create feature with specific settings
        def test_extract(code: str) -> float:
            return len(code) / 10.0  # Normalize by dividing by 10
        
        feature = FeatureConfiguration(
            name='normalized_length',
            description='Normalized code length',
            extract_fn=test_extract,
            bin_config=BinConfiguration(
                strategy='uniform',
                num_bins=5,
                min_value=0.0,
                max_value=50.0
            ),
            weight=2.0
        )
        
        manager.register_feature(feature)
        
        # Extract features multiple times - should be consistent
        test_code = "def hello(): print('world')"
        
        features1 = manager.extract_features(test_code, ['normalized_length'])
        features2 = manager.extract_features(test_code, ['normalized_length'])
        
        assert features1 == features2  # Should be deterministic
        
        # Test bin boundaries are consistent
        boundaries1 = manager.get_bin_boundaries_for_features(['normalized_length'])
        boundaries2 = manager.get_bin_boundaries_for_features(['normalized_length'])
        
        assert boundaries1 == boundaries2