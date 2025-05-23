"""
Tests for the persistence and checkpointing system.

This module tests all persistence functionality including program database
serialization, checkpointing, backup/recovery, and data integrity verification.
"""

import json
import gzip
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from alpha_evolve.persistence import (
    PersistentProgramDatabase, EvolutionCheckpoint, EvolutionState,
    SerializableProgramEntry, SerializableArchive, StorageMetadata,
    create_storage_manager
)
from alpha_evolve.program_database import ProgramEntry, MAPElitesArchive, ProgramDatabase
from alpha_evolve.controller import DistributedController
from alpha_evolve.task_utils import TaskDefinition


class TestSerializableProgramEntry:
    """Test serializable program entry functionality."""
    
    def test_to_dict_conversion(self):
        """Test converting program entry to dictionary."""
        entry = SerializableProgramEntry(
            id="test_id",
            code="def test(): pass",
            scores={"fitness": 0.8, "complexity": 5},
            features=(1, 2, 3),
            generation=10,
            parent_id="parent_id"
        )
        
        data = entry.to_dict()
        
        assert data['id'] == "test_id"
        assert data['code'] == "def test(): pass"
        assert data['scores'] == {"fitness": 0.8, "complexity": 5}
        assert data['features'] == [1, 2, 3]  # Tuple converted to list
        assert data['generation'] == 10
        assert data['parent_id'] == "parent_id"
    
    def test_from_dict_conversion(self):
        """Test creating program entry from dictionary."""
        data = {
            'id': "test_id",
            'code': "def test(): pass",
            'scores': {"fitness": 0.8, "complexity": 5},
            'features': [1, 2, 3],
            'generation': 10,
            'parent_id': "parent_id"
        }
        
        entry = SerializableProgramEntry.from_dict(data)
        
        assert entry.id == "test_id"
        assert entry.code == "def test(): pass"
        assert entry.scores == {"fitness": 0.8, "complexity": 5}
        assert entry.features == (1, 2, 3)  # List converted back to tuple
        assert entry.generation == 10
        assert entry.parent_id == "parent_id"
    
    def test_roundtrip_conversion(self):
        """Test that to_dict -> from_dict preserves data."""
        original = SerializableProgramEntry(
            id="test_id",
            code="def test(): return 42",
            scores={"objective": 0.95},
            features=(2, 3),
            generation=5
        )
        
        data = original.to_dict()
        restored = SerializableProgramEntry.from_dict(data)
        
        assert restored.id == original.id
        assert restored.code == original.code
        assert restored.scores == original.scores
        assert restored.features == original.features
        assert restored.generation == original.generation
        assert restored.parent_id == original.parent_id


class TestSerializableArchive:
    """Test serializable MAP-Elites archive functionality."""
    
    def test_archive_serialization(self):
        """Test converting MAP-Elites archive to serializable format."""
        # Create archive with sample data
        feature_bins = [list(range(3)), list(range(3))]
        archive = MAPElitesArchive(feature_bins)
        
        # Add some programs
        entry1 = ProgramEntry.create("code1", {"fitness": 0.8}, (0, 1), 1)
        entry2 = ProgramEntry.create("code2", {"fitness": 0.9}, (1, 2), 2)
        
        archive.add_program(entry1, "fitness")
        archive.add_program(entry2, "fitness")
        
        # Serialize
        serializable = SerializableArchive(archive)
        data = serializable.to_dict()
        
        assert 'feature_dimensions_bins' in data
        assert 'archive_data' in data
        assert data['feature_dimensions_bins'] == feature_bins
        assert len(data['archive_data']) == 2
    
    def test_archive_deserialization(self):
        """Test converting serializable format back to MAP-Elites archive."""
        # Create test data
        data = {
            'feature_dimensions_bins': [list(range(3)), list(range(3))],
            'archive_data': {
                '0,1': {
                    'id': 'test_id1',
                    'code': 'code1',
                    'scores': {'fitness': 0.8},
                    'features': [0, 1],
                    'generation': 1,
                    'parent_id': None
                },
                '1,2': {
                    'id': 'test_id2',
                    'code': 'code2',
                    'scores': {'fitness': 0.9},
                    'features': [1, 2],
                    'generation': 2,
                    'parent_id': None
                }
            }
        }
        
        serializable = SerializableArchive.from_dict(data)
        archive = serializable.to_map_elites_archive()
        
        assert len(archive.archive) == 2
        assert (0, 1) in archive.archive
        assert (1, 2) in archive.archive
        assert archive.archive[(0, 1)].code == 'code1'
        assert archive.archive[(1, 2)].code == 'code2'


class TestPersistentProgramDatabase:
    """Test persistent program database functionality."""
    
    def test_initialization(self):
        """Test database initialization."""
        feature_bins = [list(range(5)), list(range(5))]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db = PersistentProgramDatabase(
                feature_dimensions_bins=feature_bins,
                primary_score_key="objective",
                storage_path=temp_dir,
                auto_save_interval=10
            )
            
            assert db.database.primary_score_key == "objective"
            assert db.auto_save_interval == 10
            assert Path(temp_dir).exists()
    
    def test_add_program_with_auto_save(self):
        """Test adding programs with auto-save functionality."""
        feature_bins = [list(range(3)), list(range(3))]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db = PersistentProgramDatabase(
                feature_dimensions_bins=feature_bins,
                storage_path=temp_dir,
                auto_save_interval=2  # Save after 2 additions
            )
            
            # Mock the save method to track calls
            with patch.object(db, 'save', return_value=True) as mock_save:
                # Add first program - should not trigger save
                entry1 = ProgramEntry.create("code1", {"fitness": 0.8}, (0, 1), 1)
                db.add_program(entry1)
                mock_save.assert_not_called()
                
                # Add second program - should trigger save
                entry2 = ProgramEntry.create("code2", {"fitness": 0.9}, (1, 2), 2)
                db.add_program(entry2)
                mock_save.assert_called_once()
    
    def test_save_and_load_json(self):
        """Test saving and loading database in JSON format."""
        feature_bins = [list(range(3)), list(range(3))]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "test_db.json"
            
            # Create and populate database
            db = PersistentProgramDatabase(feature_bins, "objective")
            
            entry1 = ProgramEntry.create("def func1(): return 1", {"objective": 0.8}, (0, 1), 1)
            entry2 = ProgramEntry.create("def func2(): return 2", {"objective": 0.9}, (1, 2), 2)
            
            db.add_program(entry1)
            db.add_program(entry2)
            
            # Save database
            assert db.save(save_path) is True
            assert save_path.exists()
            
            # Create new database and load
            db2 = PersistentProgramDatabase(feature_bins, "objective")
            assert db2.load(save_path) is True
            
            # Verify data integrity
            assert len(db2.all_programs_by_id) == 2
            assert len(db2.map_elites_archive.archive) == 2
            assert db2.primary_score_key == "objective"
            
            # Check specific programs
            loaded_entry1 = db2.get_program_by_id(entry1.id)
            assert loaded_entry1 is not None
            assert loaded_entry1.code == "def func1(): return 1"
            assert loaded_entry1.scores == {"objective": 0.8}
    
    def test_save_and_load_compressed(self):
        """Test saving and loading with compression."""
        feature_bins = [list(range(2)), list(range(2))]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "test_db_compressed.json"
            
            # Create database with compression enabled
            db = PersistentProgramDatabase(
                feature_bins, "objective", 
                enable_compression=True
            )
            
            # Add some data
            entry = ProgramEntry.create("def large_func(): return 'x' * 1000", {"objective": 0.8}, (0, 1), 1)
            db.add_program(entry)
            
            # Save and verify file is compressed
            assert db.save(save_path) is True
            
            # Check if file is actually compressed
            with open(save_path, 'rb') as f:
                magic = f.read(2)
                assert magic == b'\x1f\x8b'  # Gzip magic bytes
            
            # Load and verify
            db2 = PersistentProgramDatabase(feature_bins, "objective")
            assert db2.load(save_path) is True
            assert len(db2.all_programs_by_id) == 1
    
    def test_create_backup(self):
        """Test backup creation functionality."""
        feature_bins = [list(range(2)), list(range(2))]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            db = PersistentProgramDatabase(
                feature_bins, "objective",
                storage_path=Path(temp_dir) / "database.json"
            )
            
            # Add some data
            entry = ProgramEntry.create("def test(): pass", {"objective": 0.7}, (0, 0), 1)
            db.add_program(entry)
            
            # Create backup
            backup_path = db.create_backup()
            
            assert backup_path is not None
            assert backup_path.exists()
            assert "backup" in str(backup_path)
            
            # Verify backup contains data
            db_backup = PersistentProgramDatabase(feature_bins, "objective")
            assert db_backup.load(backup_path) is True
            assert len(db_backup.all_programs_by_id) == 1
    
    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file."""
        feature_bins = [list(range(2)), list(range(2))]
        db = PersistentProgramDatabase(feature_bins, "objective")
        
        assert db.load("nonexistent_file.json") is False
    
    def test_checksum_verification(self):
        """Test data integrity verification with checksums."""
        feature_bins = [list(range(2)), list(range(2))]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            save_path = Path(temp_dir) / "checksum_test.json"
            
            # Create and save database without compression for this test
            db = PersistentProgramDatabase(feature_bins, "objective", enable_compression=False)
            entry = ProgramEntry.create("def test(): pass", {"objective": 0.8}, (0, 1), 1)
            db.add_program(entry)
            
            assert db.save(save_path) is True
            
            # Manually corrupt the file by changing content but keeping valid JSON
            with open(save_path, 'r') as f:
                data = json.load(f)
            
            # Change some data
            list(data['all_programs'].values())[0]['code'] = "def corrupted(): pass"
            
            with open(save_path, 'w') as f:
                json.dump(data, f)
            
            # Try to load - should detect corruption
            db2 = PersistentProgramDatabase(feature_bins, "objective")
            
            # Should load but warn about checksum mismatch
            with patch.object(db2, 'logger') as mock_logger:
                assert db2.load(save_path) is True  # Still loads despite corruption warning
                mock_logger.warning.assert_called_with("Checksum mismatch - data may be corrupted")


class TestEvolutionCheckpoint:
    """Test evolution checkpointing functionality."""
    
    def test_initialization(self):
        """Test checkpoint manager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_dir = Path(temp_dir) / "checkpoints"
            manager = EvolutionCheckpoint(checkpoint_dir)
            
            assert manager.checkpoint_dir == checkpoint_dir
            assert checkpoint_dir.exists()
    
    def test_save_checkpoint(self):
        """Test saving evolution checkpoint."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = EvolutionCheckpoint(temp_dir)
            
            # Create mock objects
            feature_bins = [list(range(3)), list(range(3))]
            program_db = PersistentProgramDatabase(feature_bins, "objective")
            
            # Add some test data
            entry = ProgramEntry.create("def test(): pass", {"objective": 0.8}, (0, 1), 5)
            program_db.add_program(entry)
            
            # Create mock controller
            task_def = TaskDefinition(
                problem_name="test",
                initial_code_path="test.py",
                evaluate_function_module_path="evaluator",
                evaluate_function_name="evaluate"
            )
            
            controller = MagicMock()
            controller.config = {"test": "config"}
            controller.task_definition = task_def
            
            # Save checkpoint
            checkpoint_path = manager.save_checkpoint(
                controller=controller,
                program_database=program_db,
                generation=5,
                metadata={"test_stat": 42}
            )
            
            assert checkpoint_path is not None
            assert checkpoint_path.exists()
            
            # Verify checkpoint structure
            assert (checkpoint_path / "evolution_state.json").exists()
            assert (checkpoint_path / "program_database.json").exists()
            assert (checkpoint_path / "checkpoint_metadata.json").exists()
    
    def test_load_checkpoint(self):
        """Test loading evolution checkpoint."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = EvolutionCheckpoint(temp_dir)
            
            # Create and save checkpoint first
            feature_bins = [list(range(2)), list(range(2))]
            program_db = PersistentProgramDatabase(feature_bins, "objective")
            
            entry = ProgramEntry.create("def test(): return 1", {"objective": 0.9}, (1, 1), 3)
            program_db.add_program(entry)
            
            task_def = TaskDefinition(
                problem_name="test_problem",
                initial_code_path="code.py",
                evaluate_function_module_path="evaluator",
                evaluate_function_name="evaluate"
            )
            
            controller = MagicMock()
            controller.config = {"generations": 10}
            controller.task_definition = task_def
            
            checkpoint_path = manager.save_checkpoint(controller, program_db, 3)
            
            # Load checkpoint
            loaded_data = manager.load_checkpoint(checkpoint_path)
            
            assert loaded_data is not None
            assert 'checkpoint_metadata' in loaded_data
            assert 'evolution_state' in loaded_data
            assert 'program_database' in loaded_data
            
            # Verify loaded data
            evolution_state = loaded_data['evolution_state']
            assert evolution_state.generation == 3
            assert evolution_state.controller_config == {"generations": 10}
            
            loaded_db = loaded_data['program_database']
            assert len(loaded_db.all_programs_by_id) == 1
    
    def test_list_checkpoints(self):
        """Test listing available checkpoints."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = EvolutionCheckpoint(temp_dir)
            
            # Initially no checkpoints
            checkpoints = manager.list_checkpoints()
            assert len(checkpoints) == 0
            
            # Create some checkpoints
            feature_bins = [list(range(2)), list(range(2))]
            program_db = PersistentProgramDatabase(feature_bins, "objective")
            
            controller = MagicMock()
            controller.config = {}
            controller.task_definition = TaskDefinition("test", "code.py", "evaluator", "evaluate")
            
            # Save multiple checkpoints
            checkpoint1 = manager.save_checkpoint(controller, program_db, 1)
            checkpoint2 = manager.save_checkpoint(controller, program_db, 5)
            
            # List checkpoints
            checkpoints = manager.list_checkpoints()
            assert len(checkpoints) == 2
            
            # Verify checkpoint information
            generations = [cp['generation'] for cp in checkpoints]
            assert 1 in generations
            assert 5 in generations
    
    def test_cleanup_old_checkpoints(self):
        """Test removing old checkpoints."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = EvolutionCheckpoint(temp_dir)
            
            # Create multiple checkpoints
            feature_bins = [list(range(2)), list(range(2))]
            program_db = PersistentProgramDatabase(feature_bins, "objective")
            
            controller = MagicMock()
            controller.config = {}
            controller.task_definition = TaskDefinition("test", "code.py", "evaluator", "evaluate")
            
            # Create 5 checkpoints
            checkpoints = []
            for i in range(5):
                cp = manager.save_checkpoint(controller, program_db, i)
                checkpoints.append(cp)
            
            # Verify all exist
            assert len(manager.list_checkpoints()) == 5
            
            # Cleanup, keeping only 3
            removed_count = manager.cleanup_old_checkpoints(keep_count=3)
            
            assert removed_count == 2
            assert len(manager.list_checkpoints()) == 3
            
            # Verify newest checkpoints remain
            remaining = manager.list_checkpoints()
            generations = [cp['generation'] for cp in remaining]
            assert set(generations) == {2, 3, 4}


class TestStorageManager:
    """Test integrated storage management functionality."""
    
    def test_create_storage_manager(self):
        """Test creating complete storage management system."""
        with tempfile.TemporaryDirectory() as temp_dir:
            feature_bins = [list(range(3)), list(range(3))]
            
            program_db, checkpoint_manager = create_storage_manager(
                storage_dir=temp_dir,
                feature_dimensions_bins=feature_bins,
                primary_score_key="fitness",
                enable_compression=True,
                auto_save_interval=50
            )
            
            # Verify components created
            assert isinstance(program_db, PersistentProgramDatabase)
            assert isinstance(checkpoint_manager, EvolutionCheckpoint)
            
            # Verify directory structure
            storage_path = Path(temp_dir)
            assert (storage_path / "databases").exists()
            assert (storage_path / "checkpoints").exists()
            
            # Test functionality
            entry = ProgramEntry.create("def test(): pass", {"fitness": 0.8}, (1, 2), 1)
            assert program_db.add_program(entry) is True
            
            # Test checkpoint creation
            controller = MagicMock()
            controller.config = {"test": True}
            controller.task_definition = TaskDefinition("test", "code.py", "evaluator", "evaluate")
            
            checkpoint_path = checkpoint_manager.save_checkpoint(controller, program_db, 1)
            assert checkpoint_path is not None


class TestErrorHandling:
    """Test error handling in persistence system."""
    
    def test_save_to_readonly_directory(self):
        """Test handling of save errors due to permissions."""
        feature_bins = [list(range(2)), list(range(2))]
        db = PersistentProgramDatabase(feature_bins, "objective")
        
        # Try to save to a path that doesn't exist and can't be created
        result = db.save("/nonexistent/readonly/path/database.json")
        assert result is False
    
    def test_load_corrupted_json(self):
        """Test handling of corrupted JSON files."""
        feature_bins = [list(range(2)), list(range(2))]
        db = PersistentProgramDatabase(feature_bins, "objective")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json content")
            corrupted_file = f.name
        
        try:
            result = db.load(corrupted_file)
            assert result is False
        finally:
            Path(corrupted_file).unlink()
    
    def test_checkpoint_save_failure(self):
        """Test handling of checkpoint save failures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            manager = EvolutionCheckpoint(temp_dir)
            
            # Create mock program database that fails to save
            program_db = MagicMock()
            program_db.save.return_value = False
            
            controller = MagicMock()
            controller.config = {}
            
            result = manager.save_checkpoint(controller, program_db, 1)
            assert result is None