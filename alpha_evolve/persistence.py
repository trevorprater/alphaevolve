"""
Persistent storage and checkpointing system for AlphaEvolve.

This module provides functionality for saving and loading program databases,
evolution state, and checkpoints to enable resumable evolution experiments.
"""

import json
import os
import pickle
import hashlib
import gzip
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import asdict, dataclass
import logging

from alpha_evolve.program_database import ProgramEntry, MAPElitesArchive, ProgramDatabase
from alpha_evolve.controller import DistributedController
from alpha_evolve.task_utils import TaskDefinition


@dataclass
class StorageMetadata:
    """Metadata for stored program databases and checkpoints."""
    version: str = "1.0.0"
    created_at: str = ""
    file_format: str = "json"
    compression: bool = False
    checksum: str = ""
    total_programs: int = 0
    archive_size: int = 0
    generation: int = 0
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SerializationMixin:
    """Mixin to add serialization capabilities to classes."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert object to dictionary for serialization."""
        if hasattr(self, '__dict__'):
            return self.__dict__
        else:
            # For dataclasses
            return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """Create object from dictionary."""
        return cls(**data)


class SerializableProgramEntry(ProgramEntry):
    """ProgramEntry with enhanced serialization support."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'code': self.code,
            'scores': self.scores,
            'features': list(self.features),  # Convert tuple to list for JSON
            'generation': self.generation,
            'parent_id': self.parent_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SerializableProgramEntry':
        """Create from dictionary."""
        return cls(
            id=data['id'],
            code=data['code'],
            scores=data['scores'],
            features=tuple(data['features']),  # Convert list back to tuple
            generation=data['generation'],
            parent_id=data.get('parent_id')
        )


class SerializableArchive:
    """Serializable wrapper for MAPElitesArchive."""
    
    def __init__(self, archive: MAPElitesArchive):
        self.feature_dimensions_bins = archive.feature_dimensions_bins
        self.archive_data = {}
        
        # Convert archive to serializable format
        for bin_key, program_entry in archive.archive.items():
            # Convert tuple key to string for JSON compatibility
            str_key = self._bin_key_to_string(bin_key)
            self.archive_data[str_key] = SerializableProgramEntry.from_dict(
                program_entry.to_dict() if hasattr(program_entry, 'to_dict') 
                else SerializableProgramEntry(**asdict(program_entry)).to_dict()
            ).to_dict()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'feature_dimensions_bins': self.feature_dimensions_bins,
            'archive_data': self.archive_data
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SerializableArchive':
        """Create from dictionary."""
        instance = cls.__new__(cls)
        instance.feature_dimensions_bins = data['feature_dimensions_bins']
        instance.archive_data = data['archive_data']
        return instance
    
    def to_map_elites_archive(self) -> MAPElitesArchive:
        """Convert back to MAPElitesArchive."""
        archive = MAPElitesArchive(self.feature_dimensions_bins)
        
        for str_key, program_data in self.archive_data.items():
            bin_key = self._string_to_bin_key(str_key)
            program_entry = SerializableProgramEntry.from_dict(program_data)
            archive.archive[bin_key] = program_entry
        
        return archive
    
    def _bin_key_to_string(self, bin_key: Tuple) -> str:
        """Convert tuple bin key to string."""
        return ','.join(map(str, bin_key))
    
    def _string_to_bin_key(self, str_key: str) -> Tuple:
        """Convert string back to tuple bin key."""
        parts = str_key.split(',')
        return tuple(int(part) if part.isdigit() else float(part) for part in parts)


class PersistentProgramDatabase:
    """Enhanced program database with persistence capabilities."""
    
    def __init__(
        self, 
        feature_dimensions_bins: List[List[Any]], 
        primary_score_key: str = "fitness",
        storage_path: Optional[str] = None,
        auto_save_interval: int = 100,
        enable_compression: bool = True
    ):
        """
        Initialize persistent program database.
        
        Args:
            feature_dimensions_bins: Bins for MAP-Elites feature dimensions
            primary_score_key: Primary score key for comparisons
            storage_path: Path to save database files
            auto_save_interval: Number of additions before auto-save (0 to disable)
            enable_compression: Whether to compress saved files
        """
        self.database = ProgramDatabase(feature_dimensions_bins, primary_score_key)
        self.storage_path = Path(storage_path) if storage_path else None
        self.auto_save_interval = auto_save_interval
        self.enable_compression = enable_compression
        self.additions_since_save = 0
        self.logger = logging.getLogger(__name__)
        
        # Create storage directory if specified
        if self.storage_path and self.storage_path.suffix == '':
            # It's a directory
            self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def add_program(self, program_entry: ProgramEntry) -> bool:
        """Add program and handle auto-save."""
        result = self.database.add_program(program_entry)
        
        if result:
            self.additions_since_save += 1
            
            # Auto-save if interval reached
            if (self.auto_save_interval > 0 and 
                self.additions_since_save >= self.auto_save_interval and
                self.storage_path):
                self.save()
        
        return result
    
    def save(self, file_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Save database to file.
        
        Args:
            file_path: Path to save to (overrides default storage_path)
            
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Determine save path
            save_path = Path(file_path) if file_path else self.storage_path
            if not save_path:
                raise ValueError("No storage path specified")
            
            # If path is a directory, generate filename
            if save_path.is_dir():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = save_path / f"program_database_{timestamp}.json"
            
            # Create serializable data
            serializable_archive = SerializableArchive(self.database.map_elites_archive)
            
            data = {
                'metadata': StorageMetadata(
                    file_format='json',
                    compression=self.enable_compression,
                    total_programs=len(self.database.all_programs_by_id),
                    archive_size=len(self.database.map_elites_archive.archive)
                ).__dict__,
                'primary_score_key': self.database.primary_score_key,
                'feature_dimensions_bins': self.database.map_elites_archive.feature_dimensions_bins,
                'archive': serializable_archive.to_dict(),
                'all_programs': {
                    prog_id: SerializableProgramEntry.from_dict(
                        prog.to_dict() if hasattr(prog, 'to_dict')
                        else SerializableProgramEntry(**asdict(prog)).to_dict()
                    ).to_dict()
                    for prog_id, prog in self.database.all_programs_by_id.items()
                }
            }
            
            # Calculate checksum
            data_str = json.dumps(data, sort_keys=True)
            checksum = hashlib.sha256(data_str.encode()).hexdigest()
            data['metadata']['checksum'] = checksum
            
            # Write to file (atomic operation)
            temp_path = save_path.with_suffix('.tmp')
            
            if self.enable_compression:
                with gzip.open(temp_path, 'wt', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            else:
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
            
            # Atomic move
            shutil.move(str(temp_path), str(save_path))
            
            self.additions_since_save = 0
            self.logger.info(f"Saved program database to {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save program database: {e}")
            return False
    
    def load(self, file_path: Union[str, Path]) -> bool:
        """
        Load database from file.
        
        Args:
            file_path: Path to load from
            
        Returns:
            True if load successful, False otherwise
        """
        try:
            load_path = Path(file_path)
            if not load_path.exists():
                raise FileNotFoundError(f"File not found: {load_path}")
            
            # Detect compression
            is_compressed = load_path.suffix == '.gz' or self._is_gzipped(load_path)
            
            # Load data
            if is_compressed:
                with gzip.open(load_path, 'rt', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                with open(load_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            
            # Verify checksum if present
            if 'metadata' in data and 'checksum' in data['metadata']:
                stored_checksum = data['metadata']['checksum']
                # Remove checksum for verification
                data_copy = data.copy()
                data_copy['metadata'] = data['metadata'].copy()
                del data_copy['metadata']['checksum']
                
                calculated_checksum = hashlib.sha256(
                    json.dumps(data_copy, sort_keys=True).encode()
                ).hexdigest()
                
                if stored_checksum != calculated_checksum:
                    self.logger.warning("Checksum mismatch - data may be corrupted")
            
            # Reconstruct database
            feature_dimensions_bins = data['feature_dimensions_bins']
            primary_score_key = data['primary_score_key']
            
            # Create new database
            self.database = ProgramDatabase(feature_dimensions_bins, primary_score_key)
            
            # Load programs
            for prog_id, prog_data in data['all_programs'].items():
                program_entry = SerializableProgramEntry.from_dict(prog_data)
                self.database.all_programs_by_id[prog_id] = program_entry
            
            # Reconstruct archive
            serializable_archive = SerializableArchive.from_dict(data['archive'])
            self.database.map_elites_archive = serializable_archive.to_map_elites_archive()
            
            self.additions_since_save = 0
            self.logger.info(f"Loaded program database from {load_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load program database: {e}")
            return False
    
    def create_backup(self, backup_dir: Optional[Union[str, Path]] = None) -> Optional[Path]:
        """
        Create a backup of the current database.
        
        Args:
            backup_dir: Directory to store backup (default: storage_path/backups)
            
        Returns:
            Path to backup file, or None if failed
        """
        try:
            if not backup_dir:
                if not self.storage_path:
                    raise ValueError("No backup directory or storage path specified")
                backup_dir = self.storage_path.parent / "backups"
            
            backup_path = Path(backup_dir)
            backup_path.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = backup_path / f"program_database_backup_{timestamp}.json"
            
            if self.save(backup_file):
                self.logger.info(f"Created backup at {backup_file}")
                return backup_file
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            return None
    
    def _is_gzipped(self, file_path: Path) -> bool:
        """Check if file is gzip compressed by reading magic bytes."""
        try:
            with open(file_path, 'rb') as f:
                return f.read(2) == b'\x1f\x8b'
        except:
            return False
    
    # Delegate other methods to the underlying database
    def __getattr__(self, name):
        """Delegate attribute access to the underlying database."""
        return getattr(self.database, name)


@dataclass
class EvolutionState:
    """Represents the complete state of an evolution run."""
    generation: int
    controller_config: Dict[str, Any]
    task_definition: Dict[str, Any]
    program_database_path: str
    statistics: Dict[str, Any]
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class EvolutionCheckpoint:
    """Manages checkpointing for evolution processes."""
    
    def __init__(self, checkpoint_dir: Union[str, Path]):
        """
        Initialize checkpoint manager.
        
        Args:
            checkpoint_dir: Directory to store checkpoints
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def save_checkpoint(
        self,
        controller: DistributedController,
        program_database: PersistentProgramDatabase,
        generation: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Path]:
        """
        Save evolution state to checkpoint.
        
        Args:
            controller: The evolution controller
            program_database: The program database
            generation: Current generation number
            metadata: Additional metadata to save
            
        Returns:
            Path to checkpoint file, or None if failed
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_name = f"evolution_checkpoint_gen{generation}_{timestamp}"
            checkpoint_path = self.checkpoint_dir / checkpoint_name
            checkpoint_path.mkdir(exist_ok=True)
            
            # Save program database
            db_path = checkpoint_path / "program_database.json"
            if not program_database.save(db_path):
                raise RuntimeError("Failed to save program database")
            
            # Create evolution state
            evolution_state = EvolutionState(
                generation=generation,
                controller_config=controller.config,
                task_definition=asdict(controller.task_definition),
                program_database_path=str(db_path),
                statistics=metadata or {}
            )
            
            # Save evolution state
            state_path = checkpoint_path / "evolution_state.json"
            with open(state_path, 'w') as f:
                json.dump(asdict(evolution_state), f, indent=2)
            
            # Create checkpoint metadata
            checkpoint_metadata = {
                'version': '1.0.0',
                'created_at': datetime.now().isoformat(),
                'generation': generation,
                'total_programs': len(program_database.all_programs_by_id),
                'archive_size': len(program_database.map_elites_archive.archive),
                'files': {
                    'evolution_state': 'evolution_state.json',
                    'program_database': 'program_database.json'
                }
            }
            
            metadata_path = checkpoint_path / "checkpoint_metadata.json"
            with open(metadata_path, 'w') as f:
                json.dump(checkpoint_metadata, f, indent=2)
            
            self.logger.info(f"Saved checkpoint at {checkpoint_path}")
            return checkpoint_path
            
        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")
            return None
    
    def load_checkpoint(self, checkpoint_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Load evolution state from checkpoint.
        
        Args:
            checkpoint_path: Path to checkpoint directory
            
        Returns:
            Dictionary containing loaded state, or None if failed
        """
        try:
            checkpoint_path = Path(checkpoint_path)
            if not checkpoint_path.exists():
                raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")
            
            # Load checkpoint metadata
            metadata_path = checkpoint_path / "checkpoint_metadata.json"
            with open(metadata_path, 'r') as f:
                checkpoint_metadata = json.load(f)
            
            # Load evolution state
            state_path = checkpoint_path / "evolution_state.json"
            with open(state_path, 'r') as f:
                evolution_state_data = json.load(f)
            
            evolution_state = EvolutionState(**evolution_state_data)
            
            # Load program database
            db_path = checkpoint_path / "program_database.json"
            program_database = PersistentProgramDatabase(
                feature_dimensions_bins=[],  # Will be loaded from file
                primary_score_key="fitness"
            )
            
            if not program_database.load(db_path):
                raise RuntimeError("Failed to load program database")
            
            self.logger.info(f"Loaded checkpoint from {checkpoint_path}")
            
            return {
                'checkpoint_metadata': checkpoint_metadata,
                'evolution_state': evolution_state,
                'program_database': program_database
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        List available checkpoints with metadata.
        
        Returns:
            List of checkpoint information dictionaries
        """
        checkpoints = []
        
        try:
            for item in self.checkpoint_dir.iterdir():
                if item.is_dir() and item.name.startswith('evolution_checkpoint_'):
                    metadata_path = item / "checkpoint_metadata.json"
                    if metadata_path.exists():
                        try:
                            with open(metadata_path, 'r') as f:
                                metadata = json.load(f)
                            
                            checkpoint_info = {
                                'path': str(item),
                                'name': item.name,
                                'generation': metadata.get('generation', 0),
                                'created_at': metadata.get('created_at', ''),
                                'total_programs': metadata.get('total_programs', 0),
                                'archive_size': metadata.get('archive_size', 0)
                            }
                            checkpoints.append(checkpoint_info)
                            
                        except Exception as e:
                            self.logger.warning(f"Failed to read checkpoint metadata for {item}: {e}")
        
        except Exception as e:
            self.logger.error(f"Failed to list checkpoints: {e}")
        
        # Sort by generation and creation time
        checkpoints.sort(key=lambda x: (x['generation'], x['created_at']))
        return checkpoints
    
    def cleanup_old_checkpoints(self, keep_count: int = 10) -> int:
        """
        Remove old checkpoints, keeping only the most recent ones.
        
        Args:
            keep_count: Number of checkpoints to keep
            
        Returns:
            Number of checkpoints removed
        """
        checkpoints = self.list_checkpoints()
        removed_count = 0
        
        if len(checkpoints) > keep_count:
            # Remove oldest checkpoints
            to_remove = checkpoints[:-keep_count]
            
            for checkpoint in to_remove:
                try:
                    checkpoint_path = Path(checkpoint['path'])
                    shutil.rmtree(checkpoint_path)
                    removed_count += 1
                    self.logger.info(f"Removed old checkpoint: {checkpoint_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to remove checkpoint {checkpoint['path']}: {e}")
        
        return removed_count


def create_storage_manager(
    storage_dir: Union[str, Path],
    feature_dimensions_bins: List[List[Any]],
    primary_score_key: str = "fitness",
    enable_compression: bool = True,
    auto_save_interval: int = 100
) -> Tuple[PersistentProgramDatabase, EvolutionCheckpoint]:
    """
    Create a complete storage management system.
    
    Args:
        storage_dir: Directory for all storage (databases and checkpoints)
        feature_dimensions_bins: Bins for MAP-Elites feature dimensions
        primary_score_key: Primary score key for comparisons
        enable_compression: Whether to compress saved files
        auto_save_interval: Auto-save interval for database
        
    Returns:
        Tuple of (PersistentProgramDatabase, EvolutionCheckpoint)
    """
    storage_path = Path(storage_dir)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Create database storage
    db_storage_path = storage_path / "databases"
    program_database = PersistentProgramDatabase(
        feature_dimensions_bins=feature_dimensions_bins,
        primary_score_key=primary_score_key,
        storage_path=db_storage_path,
        auto_save_interval=auto_save_interval,
        enable_compression=enable_compression
    )
    
    # Create checkpoint manager
    checkpoint_dir = storage_path / "checkpoints"
    checkpoint_manager = EvolutionCheckpoint(checkpoint_dir)
    
    return program_database, checkpoint_manager