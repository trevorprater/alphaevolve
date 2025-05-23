"""
Integration tests for diversity metrics with MAP-Elites archives.

Tests the integration of diversity metrics with advanced MAP-Elites archives,
including diversity-aware program selection and archive statistics.
"""

import pytest
import numpy as np
from typing import List, Dict, Any

from alpha_evolve.diversity_metrics import get_diversity_metric, CompositeDiversityMetric
from alpha_evolve.advanced_map_elites import CVTMAPElitesArchive, ArchiveCell
from alpha_evolve.program_database import ProgramEntry
from alpha_evolve.feature_configuration import get_feature_manager


class TestArchiveCellDiversityIntegration:
    """Test diversity-aware functionality in ArchiveCell."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.diversity_metric = get_diversity_metric()
        self.cell = ArchiveCell()
    
    def create_test_program(self, code: str, score: float = 0.5) -> ProgramEntry:
        """Create a test program entry."""
        return ProgramEntry.create(
            code=code,
            features=(0.5, 0.3),  # Simple 2D features as tuple
            scores={'fitness': score},
            generation=1
        )
    
    def test_first_program_becomes_elite(self):
        """Test that the first program becomes the elite."""
        program = self.create_test_program("def first():\n    return 1")
        
        result = self.cell.add_diversity_aware_program(program, self.diversity_metric)
        
        assert result is True
        assert self.cell.elite == program
        assert len(self.cell.alternative_elites) == 0
    
    def test_highly_diverse_program_added_as_alternative(self):
        """Test that highly diverse programs are added as alternatives."""
        # Set up elite
        elite_program = self.create_test_program("def simple():\n    return 1", 0.8)
        self.cell.elite = elite_program
        
        # Add a highly diverse program
        diverse_program = self.create_test_program("""
class ComplexClass:
    def __init__(self, config):
        self.config = config
        self.data = {}
    
    def process(self, items):
        results = []
        for item in items:
            if item.key in self.data:
                results.append(self.data[item.key])
            else:
                processed = self._complex_computation(item)
                self.data[item.key] = processed
                results.append(processed)
        return results
    
    def _complex_computation(self, item):
        # Complex computation here
        return item.value * 2
""", 0.6)
        
        result = self.cell.add_diversity_aware_program(diverse_program, self.diversity_metric)
        
        # Should be added as alternative due to high diversity
        assert result is True
        assert self.cell.elite == elite_program  # Elite unchanged
        assert diverse_program in self.cell.alternative_elites
        assert len(self.cell.diversity_scores) > 0
    
    def test_similar_program_not_added(self):
        """Test that similar programs are not added as alternatives."""
        # Set up elite
        elite_program = self.create_test_program("def add(x, y):\n    return x + y", 0.8)
        self.cell.elite = elite_program
        
        # Add a similar program
        similar_program = self.create_test_program("def add_numbers(a, b):\n    return a + b", 0.7)
        
        result = self.cell.add_diversity_aware_program(similar_program, self.diversity_metric)
        
        # Should not be added due to low diversity
        assert result is False
        assert self.cell.elite == elite_program
        assert similar_program not in self.cell.alternative_elites
    
    def test_alternative_elite_limit_enforcement(self):
        """Test that alternative elite limit is enforced."""
        # Set up elite
        elite_program = self.create_test_program("def original():\n    return 0", 0.8)
        self.cell.elite = elite_program
        
        # Add multiple diverse programs (more than the limit)
        diverse_codes = [
            "class A:\n    def method(self): return 1",
            "def recursive(n):\n    return 1 if n <= 1 else n * recursive(n-1)",
            "for i in range(10):\n    print(i)",
            "import numpy as np\ndef process(data): return np.mean(data)",
            "async def fetch_data(): return await some_call()",
            "def generator(): yield from range(100)",
            "with open('file.txt') as f: content = f.read()"
        ]
        
        max_alternatives = 3
        for i, code in enumerate(diverse_codes):
            program = self.create_test_program(code, 0.6 + i * 0.01)
            self.cell.add_diversity_aware_program(program, self.diversity_metric, max_alternatives)
        
        # Should not exceed the limit
        assert len(self.cell.alternative_elites) <= max_alternatives
        assert self.cell.elite == elite_program
    
    def test_get_diverse_sample(self):
        """Test getting diverse samples from cell."""
        # Set up elite and alternatives
        elite_program = self.create_test_program("def elite():\n    return 1", 0.9)
        self.cell.elite = elite_program
        
        alt1 = self.create_test_program("class Alt1:\n    pass", 0.7)
        alt2 = self.create_test_program("def alt2():\n    yield 1", 0.8)
        self.cell.alternative_elites = [alt1, alt2]
        
        # Get samples multiple times
        samples = [self.cell.get_diverse_sample(self.diversity_metric) for _ in range(10)]
        
        # Should get variety of samples (check by ID since ProgramEntry is not hashable)
        unique_sample_ids = set(sample.id for sample in samples)
        assert len(unique_sample_ids) >= 2  # Should get different programs
        valid_ids = {elite_program.id, alt1.id, alt2.id}
        assert all(sample.id in valid_ids for sample in samples)
    
    def test_diversity_statistics(self):
        """Test diversity statistics calculation."""
        # Set up cell with diversity history
        elite_program = self.create_test_program("def test():\n    return 1", 0.8)
        self.cell.elite = elite_program
        
        # Simulate adding diverse programs to build history
        diverse_programs = [
            self.create_test_program("class Test:\n    pass", 0.6),
            self.create_test_program("def generator():\n    yield 1", 0.7),
            self.create_test_program("[x for x in range(10)]", 0.5)
        ]
        
        for program in diverse_programs:
            self.cell.add_diversity_aware_program(program, self.diversity_metric)
        
        stats = self.cell.get_diversity_statistics()
        
        assert isinstance(stats, dict)
        assert 'avg_diversity' in stats
        assert 'max_diversity' in stats
        assert 'diversity_trend' in stats
        assert 'alternative_count' in stats
        assert stats['alternative_count'] == len(self.cell.alternative_elites)


class TestCVTMAPElitesArchiveDiversityIntegration:
    """Test diversity integration with CVT-MAP-Elites archive."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.feature_manager = get_feature_manager()
        self.archive = CVTMAPElitesArchive(
            feature_dimensions=2,
            num_centroids=50,
            feature_manager=self.feature_manager
        )
    
    def create_test_program(self, code: str, features: List[float], score: float = 0.5) -> ProgramEntry:
        """Create a test program entry with specific features."""
        return ProgramEntry.create(
            code=code,
            features=tuple(features),  # Convert to tuple
            scores={'fitness': score},
            generation=1
        )
    
    def test_diversity_mode_enabled_by_default(self):
        """Test that diversity mode is enabled by default."""
        assert self.archive.get_diversity_mode() is True
    
    def test_diversity_mode_toggle(self):
        """Test toggling diversity mode."""
        self.archive.set_diversity_mode(False)
        assert self.archive.get_diversity_mode() is False
        
        self.archive.set_diversity_mode(True)
        assert self.archive.get_diversity_mode() is True
    
    def test_diverse_program_addition(self):
        """Test that diverse programs are added to archive."""
        # Add initial program
        program1 = self.create_test_program(
            "def simple():\n    return 1", 
            [0.2, 0.3], 
            0.8
        )
        result1 = self.archive.add_program(program1, 'fitness')
        assert result1 is True
        
        # Add highly diverse program to same region
        program2 = self.create_test_program(
            """
class ComplexProcessor:
    def __init__(self, config_data):
        self.config = config_data
        self.cache = {}
        self.metrics = defaultdict(int)
    
    def process_batch(self, items):
        results = []
        for item in items:
            if self._should_process(item):
                processed = self._apply_transformations(item)
                results.append(processed)
                self.metrics['processed'] += 1
            else:
                self.metrics['skipped'] += 1
        return results
    
    def _should_process(self, item):
        return item.priority > 0 and item.valid
    
    def _apply_transformations(self, item):
        # Complex transformation logic
        transformed = item.data
        for transform in self.config.transforms:
            transformed = transform.apply(transformed)
        return transformed
""", 
            [0.25, 0.35],  # Close features to trigger same cell
            0.6  # Lower fitness but high diversity
        )
        
        result2 = self.archive.add_program(program2, 'fitness')
        # Should be added due to diversity even with lower fitness
        assert result2 is True
    
    def test_get_diverse_elites(self):
        """Test getting diverse elites from archive."""
        # Add multiple programs with varying diversity
        programs = [
            ("def func1():\n    return 1", [0.1, 0.1], 0.9),
            ("class Class1:\n    def method(self): return 2", [0.3, 0.3], 0.8),
            ("def generator():\n    yield from range(10)", [0.5, 0.5], 0.7),
            ("[x**2 for x in range(100) if x % 2 == 0]", [0.7, 0.7], 0.6),
            ("async def async_func():\n    return await some_call()", [0.9, 0.9], 0.5)
        ]
        
        for code, features, score in programs:
            program = self.create_test_program(code, features, score)
            self.archive.add_program(program, 'fitness')
        
        # Get diverse elites
        diverse_elites = self.archive.get_diverse_elites(3, diversity_threshold=0.2)
        
        assert len(diverse_elites) <= 3
        assert len(diverse_elites) >= 1
        
        # Check that selected elites are indeed diverse
        if len(diverse_elites) >= 2:
            diversity_metric = get_diversity_metric()
            for i in range(len(diverse_elites)):
                for j in range(i + 1, len(diverse_elites)):
                    div_score = diversity_metric.calculate_diversity(
                        diverse_elites[i].code, diverse_elites[j].code
                    )
                    assert div_score.total_score >= 0.2  # Lower threshold for realistic diversity
    
    def test_diversity_statistics(self):
        """Test archive diversity statistics."""
        # Add programs to archive
        programs = [
            ("def simple():\n    return 1", [0.2, 0.2], 0.8),
            ("class Complex:\n    def __init__(self): pass", [0.4, 0.4], 0.7),
            ("for i in range(10):\n    print(i)", [0.6, 0.6], 0.6),
            ("import sys\ndef main(): sys.exit(0)", [0.8, 0.8], 0.5)
        ]
        
        for code, features, score in programs:
            program = self.create_test_program(code, features, score)
            self.archive.add_program(program, 'fitness')
        
        stats = self.archive.get_diversity_statistics()
        
        assert isinstance(stats, dict)
        assert 'avg_diversity_per_cell' in stats
        assert 'max_diversity_per_cell' in stats
        assert 'total_alternative_elites' in stats
        assert 'cells_with_alternatives' in stats
        assert 'archive_diversity_score' in stats
        assert 'diversity_mode_enabled' in stats
        
        assert stats['diversity_mode_enabled'] is True
        assert 0.0 <= stats['archive_diversity_score'] <= 1.0
    
    def test_archive_diversity_calculation(self):
        """Test overall archive diversity calculation."""
        # Add highly diverse programs
        highly_diverse_programs = [
            ("def simple_function():\n    return 42", [0.1, 0.9], 0.8),
            ("""
class AdvancedProcessor:
    def __init__(self, config):
        self.config = config
        self.state = {}
    
    async def process_stream(self, data_stream):
        async for batch in data_stream:
            results = await self._process_batch(batch)
            yield results
""", [0.9, 0.1], 0.7),
            ("""
def recursive_algorithm(data, depth=0):
    if depth > 10:
        return data
    
    transformed = []
    for item in data:
        if isinstance(item, list):
            result = recursive_algorithm(item, depth + 1)
        else:
            result = complex_transformation(item)
        transformed.append(result)
    
    return transformed
""", [0.5, 0.5], 0.6),
            ("[item.process() for item in data if item.is_valid()]", [0.3, 0.7], 0.5)
        ]
        
        for code, features, score in highly_diverse_programs:
            program = self.create_test_program(code, features, score)
            self.archive.add_program(program, 'fitness')
        
        # Calculate diversity statistics
        stats = self.archive.get_diversity_statistics()
        
        # Archive with diverse programs should have reasonable diversity score
        assert stats['archive_diversity_score'] > 0.2
    
    def test_diversity_mode_disabled_behavior(self):
        """Test behavior when diversity mode is disabled."""
        self.archive.set_diversity_mode(False)
        
        # Add programs - should only use quality-based selection
        program1 = self.create_test_program("def test1():\n    return 1", [0.5, 0.5], 0.8)
        program2 = self.create_test_program("def test2():\n    return 2", [0.5, 0.5], 0.7)  # Exactly same cell, lower quality
        
        result1 = self.archive.add_program(program1, 'fitness')
        result2 = self.archive.add_program(program2, 'fitness')
        
        assert result1 is True
        assert result2 is False  # Should not be added due to lower quality
        
        # get_diverse_elites should fall back to get_random_elites
        diverse_elites = self.archive.get_diverse_elites(5)
        random_elites = self.archive.get_random_elites(5)
        
        # Should behave the same when diversity mode is disabled
        assert len(diverse_elites) == len(random_elites)


class TestDiversityMetricsPerformanceIntegration:
    """Test performance of diversity metrics in archive context."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.archive = CVTMAPElitesArchive(feature_dimensions=2, num_centroids=100)
    
    def test_large_archive_diversity_performance(self):
        """Test diversity calculations with larger archive."""
        import time
        
        # Generate diverse programs
        program_templates = [
            "def func_{i}():\n    return {i}",
            "class Class_{i}:\n    def method(self): return {i}",
            "lambda x: x + {i}",
            "[x + {i} for x in range(10)]",
            "{{'{i}': value for value in range({i})}}",
        ]
        
        # Add many programs to archive
        for i in range(50):
            template = program_templates[i % len(program_templates)]
            code = template.format(i=i)
            features = [np.random.random(), np.random.random()]
            score = np.random.random()
            
            program = ProgramEntry.create(
                code=code,
                features=tuple(features),
                scores={'fitness': score},
                generation=1
            )
            self.archive.add_program(program, 'fitness')
        
        # Test diversity statistics performance
        start_time = time.time()
        stats = self.archive.get_diversity_statistics()
        end_time = time.time()
        
        # Should complete in reasonable time
        assert end_time - start_time < 2.0  # Less than 2 seconds
        assert isinstance(stats, dict)
        assert 'archive_diversity_score' in stats
    
    def test_diverse_elites_selection_performance(self):
        """Test performance of diverse elite selection."""
        import time
        
        # Add programs to archive
        for i in range(30):
            code = f"""
def function_{i}(data):
    result = []
    for item in data:
        if item > {i}:
            result.append(item * {i})
        else:
            result.append(item + {i})
    return result
"""
            features = [np.random.random(), np.random.random()]
            score = np.random.random()
            
            program = ProgramEntry.create(
                code=code,
                features=tuple(features),
                scores={'fitness': score},
                generation=1
            )
            self.archive.add_program(program, 'fitness')
        
        # Test diverse elites selection performance
        start_time = time.time()
        diverse_elites = self.archive.get_diverse_elites(10, diversity_threshold=0.2)
        end_time = time.time()
        
        # Should complete in reasonable time
        assert end_time - start_time < 5.0  # Less than 5 seconds (diversity calculation can be expensive)
        assert len(diverse_elites) <= 10
        assert all(isinstance(elite, ProgramEntry) for elite in diverse_elites)


if __name__ == "__main__":
    pytest.main([__file__])