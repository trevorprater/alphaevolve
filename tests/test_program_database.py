"""
Tests for the program_database module.
"""

import pytest
import uuid
from typing import Dict, Tuple
from alpha_evolve.program_database import ProgramEntry, MAPElitesArchive, ProgramDatabase


class TestProgramEntry:
    """Tests for the ProgramEntry class."""

    def test_program_entry_initialization(self):
        """Test ProgramEntry initialization with all required fields."""
        # Arrange
        entry_id = "test-id-123"
        code = "def example(): return 42"
        scores = {"performance": 0.8, "complexity": 0.3}
        features = (10, 0.5)
        generation = 5
        parent_id = "parent-id-456"

        # Act
        entry = ProgramEntry(
            id=entry_id,
            code=code,
            scores=scores,
            features=features,
            generation=generation,
            parent_id=parent_id
        )

        # Assert
        assert entry.id == entry_id
        assert entry.code == code
        assert entry.scores == scores
        assert entry.features == features
        assert entry.generation == generation
        assert entry.parent_id == parent_id

    def test_program_entry_initialization_without_parent(self):
        """Test ProgramEntry initialization without a parent_id."""
        # Arrange
        entry_id = "test-id-123"
        code = "def example(): return 42"
        scores = {"performance": 0.8, "complexity": 0.3}
        features = (10, 0.5)
        generation = 5

        # Act
        entry = ProgramEntry(
            id=entry_id,
            code=code,
            scores=scores,
            features=features,
            generation=generation
        )

        # Assert
        assert entry.id == entry_id
        assert entry.code == code
        assert entry.scores == scores
        assert entry.features == features
        assert entry.generation == generation
        assert entry.parent_id is None

    def test_program_entry_factory_method(self, monkeypatch):
        """Test the create factory method for ProgramEntry with a mocked UUID."""
        # Arrange
        mock_uuid = "mock-uuid-123"
        monkeypatch.setattr(uuid, "uuid4", lambda: type("MockUUID", (), {"hex": mock_uuid})())
        
        code = "def example(): return 42"
        scores = {"performance": 0.8, "complexity": 0.3}
        features = (10, 0.5)
        generation = 5
        parent_id = "parent-id-456"

        # Act
        entry = ProgramEntry.create(
            code=code,
            scores=scores,
            features=features,
            generation=generation,
            parent_id=parent_id
        )

        # Assert
        assert entry.id == mock_uuid
        assert entry.code == code
        assert entry.scores == scores
        assert entry.features == features
        assert entry.generation == generation
        assert entry.parent_id == parent_id


class TestMAPElitesArchive:
    """Tests for the MAPElitesArchive class."""

    @pytest.fixture
    def feature_dimensions_bins(self):
        """Fixture for feature dimensions bins."""
        return [[0, 10, 20], [0.0, 0.5, 1.0]]

    @pytest.fixture
    def empty_archive(self, feature_dimensions_bins):
        """Fixture for an empty MAP-Elites archive."""
        return MAPElitesArchive(feature_dimensions_bins)

    @pytest.fixture
    def program_entry_factory(self):
        """Factory fixture for creating ProgramEntry instances."""
        def _create_program_entry(
            code: str = "def example(): return 42",
            scores: Dict[str, float] = None,
            features: Tuple = None,
            generation: int = 1,
            parent_id: str = None
        ) -> ProgramEntry:
            if scores is None:
                scores = {"performance": 0.8, "complexity": 0.3}
            if features is None:
                features = (5, 0.25)
            
            return ProgramEntry.create(
                code=code,
                scores=scores,
                features=features,
                generation=generation,
                parent_id=parent_id
            )
        return _create_program_entry

    def test_map_elites_archive_initialization(self, feature_dimensions_bins):
        """Test MAPElitesArchive initialization."""
        # Act
        archive = MAPElitesArchive(feature_dimensions_bins)

        # Assert
        assert archive.feature_dimensions_bins == feature_dimensions_bins
        assert archive.archive == {}

    def test_get_feature_bin_key_valid(self, empty_archive):
        """Test _get_feature_bin_key with features mapping to valid bins."""
        # Test cases for valid features
        test_cases = [
            ((5, 0.25), (0, 0)),  # Middle of first bins
            ((15, 0.75), (1, 1))  # Middle of second bins
        ]

        for features, expected_bin_key in test_cases:
            # Act
            bin_key = empty_archive._get_feature_bin_key(features)

            # Assert
            assert bin_key == expected_bin_key

    def test_get_feature_bin_key_bin_edges(self, empty_archive):
        """Test _get_feature_bin_key with features exactly on bin edges."""
        # Test cases for features on bin edges
        test_cases = [
            ((0, 0.0), (0, 0)),   # Lower edges of first bins
            ((10, 0.5), (1, 1)),  # Exactly on the boundary (belongs to second bins)
            ((20, 1.0), (1, 1))   # Upper edges (should be in the second bins)
        ]

        for features, expected_bin_key in test_cases:
            # Act
            bin_key = empty_archive._get_feature_bin_key(features)

            # Assert
            assert bin_key == expected_bin_key

    def test_get_feature_bin_key_out_of_bounds(self, empty_archive):
        """Test _get_feature_bin_key with features out of defined bins."""
        # Test cases for out of bounds features
        test_cases = [
            ((-1, 0.25), None),  # First feature below lower bound
            ((5, -0.1), None),   # Second feature below lower bound
            ((25, 0.25), (1, 0))  # First feature above upper bound (should be in bin 1 as per implementation)
        ]

        for features, expected_result in test_cases:
            # Act
            bin_key = empty_archive._get_feature_bin_key(features)

            # Assert
            assert bin_key == expected_result

    def test_get_feature_bin_key_wrong_dimension(self, empty_archive):
        """Test _get_feature_bin_key with features of wrong dimension."""
        # Arrange
        features = (5, 0.25, 30)  # 3 dimensions, but archive only has 2

        # Act
        bin_key = empty_archive._get_feature_bin_key(features)

        # Assert
        assert bin_key is None

    def test_add_program_to_empty_cell(self, empty_archive, program_entry_factory):
        """Test adding a program to an empty cell in the archive."""
        # Arrange
        program_entry = program_entry_factory(
            features=(5, 0.25),
            scores={"performance": 0.8}
        )

        # Act
        result = empty_archive.add_program(program_entry, "performance")

        # Assert
        assert result is True
        bin_key = (0, 0)  # Expected bin key for features (5, 0.25)
        assert bin_key in empty_archive.archive
        assert empty_archive.archive[bin_key] == program_entry

    def test_add_better_program_to_occupied_cell(self, empty_archive, program_entry_factory):
        """Test adding a better program to an already occupied cell."""
        # Arrange - Add initial program
        initial_program = program_entry_factory(
            features=(5, 0.25),
            scores={"performance": 0.6}
        )
        empty_archive.add_program(initial_program, "performance")

        # Better program with the same features
        better_program = program_entry_factory(
            features=(5, 0.25),
            scores={"performance": 0.9}
        )

        # Act
        result = empty_archive.add_program(better_program, "performance")

        # Assert
        assert result is True
        bin_key = (0, 0)  # Expected bin key for features (5, 0.25)
        assert empty_archive.archive[bin_key] == better_program

    def test_add_worse_program_to_occupied_cell(self, empty_archive, program_entry_factory):
        """Test adding a worse program to an already occupied cell."""
        # Arrange - Add initial program
        initial_program = program_entry_factory(
            features=(5, 0.25),
            scores={"performance": 0.8}
        )
        empty_archive.add_program(initial_program, "performance")

        # Worse program with the same features
        worse_program = program_entry_factory(
            features=(5, 0.25),
            scores={"performance": 0.5}
        )

        # Act
        result = empty_archive.add_program(worse_program, "performance")

        # Assert
        assert result is False
        bin_key = (0, 0)  # Expected bin key for features (5, 0.25)
        assert empty_archive.archive[bin_key] == initial_program  # Original program should remain

    def test_add_program_with_out_of_bounds_features(self, empty_archive, program_entry_factory):
        """Test adding a program with features that are out of the defined bins."""
        # Arrange
        program_entry = program_entry_factory(
            features=(-5, 0.25),  # First feature is out of bounds
            scores={"performance": 0.8}
        )

        # Act
        result = empty_archive.add_program(program_entry, "performance")

        # Assert
        assert result is False
        assert len(empty_archive.archive) == 0  # Archive should remain empty

    def test_add_program_with_missing_score_key(self, empty_archive, program_entry_factory):
        """Test adding a program with a missing score key."""
        # Arrange
        program_entry = program_entry_factory(
            features=(5, 0.25),
            scores={"complexity": 0.3}  # No "performance" key
        )

        # Act & Assert
        with pytest.raises(KeyError):
            empty_archive.add_program(program_entry, "performance")

    def test_get_elite_existing(self, empty_archive, program_entry_factory):
        """Test getting an existing elite from the archive."""
        # Arrange
        program_entry = program_entry_factory(
            features=(5, 0.25),
            scores={"performance": 0.8}
        )
        empty_archive.add_program(program_entry, "performance")

        # Act
        elite = empty_archive.get_elite((5, 0.25))

        # Assert
        assert elite is program_entry

    def test_get_elite_non_existent(self, empty_archive):
        """Test trying to get an elite from a bin that doesn't exist."""
        # Act
        elite = empty_archive.get_elite((5, 0.25))

        # Assert
        assert elite is None

    def test_get_elite_out_of_bounds(self, empty_archive):
        """Test trying to get an elite with features out of bounds."""
        # Act
        elite = empty_archive.get_elite((-5, 0.25))

        # Assert
        assert elite is None

    def test_get_random_elites_specific_count(self, empty_archive, program_entry_factory):
        """Test getting a specific number of random elites."""
        # Arrange - Add several programs to different bins
        programs = [
            program_entry_factory(features=(5, 0.25), scores={"performance": 0.8}),
            program_entry_factory(features=(15, 0.25), scores={"performance": 0.7}),
            program_entry_factory(features=(5, 0.75), scores={"performance": 0.9}),
            program_entry_factory(features=(15, 0.75), scores={"performance": 0.6})
        ]
        
        for program in programs:
            empty_archive.add_program(program, "performance")

        # Act
        random_elites = empty_archive.get_random_elites(2)

        # Assert
        assert len(random_elites) == 2
        assert all(elite in programs for elite in random_elites)
        
    def test_get_random_elites_fewer_available(self, empty_archive, program_entry_factory):
        """Test getting more elites than are available."""
        # Arrange - Add a couple of programs
        programs = [
            program_entry_factory(features=(5, 0.25), scores={"performance": 0.8}),
            program_entry_factory(features=(15, 0.25), scores={"performance": 0.7})
        ]
        
        for program in programs:
            empty_archive.add_program(program, "performance")

        # Act
        random_elites = empty_archive.get_random_elites(5)  # Ask for more than available

        # Assert
        assert len(random_elites) == 2  # Should return all available elites
        # Can't use set comparison because ProgramEntry is not hashable
        assert len(random_elites) == len(programs)
        assert all(any(elite.id == p.id for p in programs) for elite in random_elites)

    def test_get_random_elites_empty_archive(self, empty_archive):
        """Test getting random elites from an empty archive."""
        # Act
        random_elites = empty_archive.get_random_elites(3)

        # Assert
        assert random_elites == []


class TestProgramDatabase:
    """Tests for the ProgramDatabase class."""

    @pytest.fixture
    def feature_dimensions_bins(self):
        """Fixture for feature dimensions bins."""
        return [[0, 10, 20], [0.0, 0.5, 1.0]]

    @pytest.fixture
    def empty_database(self, feature_dimensions_bins):
        """Fixture for an empty program database."""
        return ProgramDatabase(feature_dimensions_bins)

    @pytest.fixture
    def program_entry_factory(self):
        """Factory fixture for creating ProgramEntry instances."""
        def _create_program_entry(
            code: str = "def example(): return 42",
            scores: Dict[str, float] = None,
            features: Tuple = None,
            generation: int = 1,
            parent_id: str = None
        ) -> ProgramEntry:
            if scores is None:
                scores = {"fitness": 0.8, "complexity": 0.3}
            if features is None:
                features = (5, 0.25)
            
            return ProgramEntry.create(
                code=code,
                scores=scores,
                features=features,
                generation=generation,
                parent_id=parent_id
            )
        return _create_program_entry

    @pytest.fixture
    def populated_database(self, empty_database, program_entry_factory):
        """Fixture for a database populated with several program entries."""
        programs = [
            program_entry_factory(features=(5, 0.25), scores={"fitness": 0.8}),
            program_entry_factory(features=(15, 0.25), scores={"fitness": 0.7}),
            program_entry_factory(features=(5, 0.75), scores={"fitness": 0.9}),
            program_entry_factory(features=(15, 0.75), scores={"fitness": 0.6})
        ]
        
        for program in programs:
            empty_database.add_program(program)
            
        return empty_database, programs

    def test_program_database_initialization(self, feature_dimensions_bins):
        """Test ProgramDatabase initialization."""
        # Act
        database = ProgramDatabase(feature_dimensions_bins)

        # Assert
        assert isinstance(database.map_elites_archive, MAPElitesArchive)
        assert database.map_elites_archive.feature_dimensions_bins == feature_dimensions_bins
        assert database.primary_score_key == "fitness"  # default value
        assert database.all_programs_by_id == {}

    def test_program_database_initialization_custom_score_key(self, feature_dimensions_bins):
        """Test ProgramDatabase initialization with a custom primary score key."""
        # Act
        database = ProgramDatabase(feature_dimensions_bins, primary_score_key="performance")

        # Assert
        assert database.primary_score_key == "performance"

    def test_add_program(self, empty_database, program_entry_factory, monkeypatch):
        """Test adding a program to the database."""
        # Arrange
        program_entry = program_entry_factory()
        
        # Mock MAPElitesArchive.add_program to return True
        add_program_called = False
        original_add_program = MAPElitesArchive.add_program
        
        def mock_add_program(self, program, primary_score_key):
            nonlocal add_program_called
            add_program_called = True
            assert program is program_entry
            assert primary_score_key == "fitness"
            return True
            
        monkeypatch.setattr(MAPElitesArchive, "add_program", mock_add_program)
        
        # Act
        result = empty_database.add_program(program_entry)
        
        # Restore original method
        monkeypatch.setattr(MAPElitesArchive, "add_program", original_add_program)
        
        # Assert
        assert result is True
        assert add_program_called is True
        assert program_entry.id in empty_database.all_programs_by_id
        assert empty_database.all_programs_by_id[program_entry.id] is program_entry

    def test_add_program_not_added_to_archive(self, empty_database, program_entry_factory, monkeypatch):
        """Test adding a program that's not added to the archive."""
        # Arrange
        program_entry = program_entry_factory()
        
        # Mock MAPElitesArchive.add_program to return False
        original_add_program = MAPElitesArchive.add_program
        
        def mock_add_program(self, program, primary_score_key):
            return False
            
        monkeypatch.setattr(MAPElitesArchive, "add_program", mock_add_program)
        
        # Act
        result = empty_database.add_program(program_entry)
        
        # Restore original method
        monkeypatch.setattr(MAPElitesArchive, "add_program", original_add_program)
        
        # Assert
        assert result is False
        assert program_entry.id in empty_database.all_programs_by_id  # Still added to all_programs_by_id

    def test_get_program_by_id_existing(self, empty_database, program_entry_factory):
        """Test retrieving an existing program by ID."""
        # Arrange
        program_entry = program_entry_factory()
        empty_database.add_program(program_entry)
        
        # Act
        retrieved_program = empty_database.get_program_by_id(program_entry.id)
        
        # Assert
        assert retrieved_program is program_entry

    def test_get_program_by_id_non_existent(self, empty_database):
        """Test retrieving a non-existent program by ID."""
        # Act
        retrieved_program = empty_database.get_program_by_id("non-existent-id")
        
        # Assert
        assert retrieved_program is None

    def test_sample_programs_for_prompting_enough_elites(self, populated_database, monkeypatch):
        """Test sampling programs when enough elites are available."""
        # Arrange
        database, all_programs = populated_database
        
        # Mock MAPElitesArchive.get_random_elites to return controlled results
        original_get_random_elites = MAPElitesArchive.get_random_elites
        
        def mock_get_random_elites(self, count):
            # Return all programs when requested, so we can test the split logic
            return all_programs
            
        monkeypatch.setattr(MAPElitesArchive, "get_random_elites", mock_get_random_elites)
        
        # Act
        num_parents = 2
        num_inspirations = 2
        parents, inspirations = database.sample_programs_for_prompting(num_parents, num_inspirations)
        
        # Restore original method
        monkeypatch.setattr(MAPElitesArchive, "get_random_elites", original_get_random_elites)
        
        # Assert
        assert len(parents) == num_parents
        assert len(inspirations) == num_inspirations
        assert parents == all_programs[:num_parents]
        assert inspirations == all_programs[num_parents:num_parents + num_inspirations]

    def test_sample_programs_for_prompting_not_enough_elites(self, populated_database, monkeypatch):
        """Test sampling programs when not enough elites are available."""
        # Arrange
        database, all_programs = populated_database
        
        # Mock MAPElitesArchive.get_random_elites to return fewer elites than requested
        original_get_random_elites = MAPElitesArchive.get_random_elites
        
        def mock_get_random_elites(self, count):
            # Only return 2 programs
            return all_programs[:2]
            
        monkeypatch.setattr(MAPElitesArchive, "get_random_elites", mock_get_random_elites)
        
        # Act
        num_parents = 3  # More than available
        num_inspirations = 2
        parents, inspirations = database.sample_programs_for_prompting(num_parents, num_inspirations)
        
        # Restore original method
        monkeypatch.setattr(MAPElitesArchive, "get_random_elites", original_get_random_elites)
        
        # Assert
        assert len(parents) == 2  # All available elites used as parents
        assert len(inspirations) == 0  # No elites left for inspirations
        assert parents == all_programs[:2]

    def test_sample_programs_for_prompting_empty_archive(self, empty_database):
        """Test sampling programs from an empty archive."""
        # Act
        parents, inspirations = empty_database.sample_programs_for_prompting(2, 3)
        
        # Assert
        assert parents == []
        assert inspirations == []

    def test_trigger_migration(self, empty_database, capfd):
        """Test the trigger_migration method."""
        # Arrange
        other_db = ProgramDatabase([[0, 10, 20], [0.0, 0.5, 1.0]])
        num_to_migrate = 5
        
        # Act
        empty_database.trigger_migration(other_db, num_to_migrate)
        
        # Assert
        out, err = capfd.readouterr()
        assert "Migration of 5 programs triggered (not yet implemented)" in out
        
    def test_get_best_program_empty_archive(self, empty_database):
        """Test getting the best program from an empty archive."""
        # Act
        best_program = empty_database.get_best_program()
        
        # Assert
        assert best_program is None
        
    def test_get_best_program_found(self, populated_database):
        """Test getting the best program from a populated archive."""
        # Arrange
        database, all_programs = populated_database
        # The program with the highest fitness is the third one (index 2) with 0.9
        expected_best = next(p for p in all_programs if p.scores["fitness"] == 0.9)
        
        # Act
        best_program = database.get_best_program()
        
        # Assert
        assert best_program is not None
        assert best_program.scores["fitness"] == 0.9
        assert best_program.id == expected_best.id
        
    def test_get_best_program_missing_score_key(self, empty_database, program_entry_factory):
        """Test getting the best program when score key is missing."""
        # Arrange
        program_with_score = program_entry_factory(
            features=(5, 0.25),
            scores={"fitness": 0.8}
        )
        program_without_score = program_entry_factory(
            features=(15, 0.25),
            scores={"performance": 0.9}  # Missing the primary score key "fitness"
        )
        
        # Add both programs to the database
        empty_database.add_program(program_with_score)
        
        # Directly add to the archive to bypass score key validation
        bin_key = empty_database.map_elites_archive._get_feature_bin_key(program_without_score.features)
        empty_database.map_elites_archive.archive[bin_key] = program_without_score
        
        # Act/Assert
        with pytest.raises(KeyError):
            empty_database.get_best_program()