"""
This module defines the core data structures for the Program Database,
specifically ProgramEntry and MAPElitesArchive.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import random
import uuid


@dataclass
class ProgramEntry:
    """
    Represents a single program variant in the evolution process.
    
    Attributes:
        id: Unique identifier for the program entry
        code: The program's source code
        scores: Dictionary mapping metric names to their float values
        features: Tuple of phenotypic features used for MAP-Elites binning
        parent_id: ID of the parent entry that generated this one (if any)
        generation: The generation number in the evolutionary process
    """
    id: str
    code: str
    scores: Dict[str, float]
    features: Tuple
    generation: int
    parent_id: Optional[str] = None
    
    @classmethod
    def create(cls, code: str, scores: Dict[str, float], features: Tuple, 
               generation: int, parent_id: Optional[str] = None) -> 'ProgramEntry':
        """
        Factory method to create a new ProgramEntry with a generated UUID.
        
        Args:
            code: The program's source code
            scores: Dictionary mapping metric names to their float values
            features: Tuple of phenotypic features
            generation: The generation number
            parent_id: ID of the parent entry (if any)
            
        Returns:
            A new ProgramEntry instance with a unique ID
        """
        return cls(
            id=uuid.uuid4().hex,
            code=code,
            scores=scores,
            features=features,
            generation=generation,
            parent_id=parent_id
        )


class MAPElitesArchive:
    """
    Implements a MAP-Elites archive for storing program variants.
    
    The archive stores the best-performing program variant (elite) for each
    discrete combination of feature values.
    """
    
    def __init__(self, feature_dimensions_bins: List[List[Any]]):
        """
        Initialize a MAP-Elites archive.
        
        Args:
            feature_dimensions_bins: A list of lists, where each inner list defines
                the bin boundaries for a feature dimension. For example:
                [[0, 10, 20], [0.1, 0.5, 1.0]] means the first feature is binned by
                <10, 10-19, >=20 and the second by <0.1, 0.1-0.49, >=0.5.
        """
        self.feature_dimensions_bins = feature_dimensions_bins
        # Archive to store the elites, indexed by bin keys (tuples of bin indices)
        self.archive: Dict[Tuple[int, ...], ProgramEntry] = {}
    
    def _get_feature_bin_key(self, features: Tuple) -> Optional[Tuple[int, ...]]:
        """
        Convert raw feature values to bin indices.
        
        Args:
            features: A tuple of raw feature values
            
        Returns:
            A tuple of bin indices corresponding to the features, or None if any
            feature falls outside the defined bins
        """
        if len(features) != len(self.feature_dimensions_bins):
            return None
        
        bin_indices = []
        
        for i, feature_value in enumerate(features):
            bins = self.feature_dimensions_bins[i]
            
            # Find the bin for this feature
            bin_index = None
            for j in range(len(bins) - 1):
                if bins[j] <= feature_value < bins[j + 1]:
                    bin_index = j
                    break
            
            # Handle the case where the value is >= the last bin boundary
            if bin_index is None and feature_value >= bins[-1]:
                bin_index = len(bins) - 2
            
            # If the feature value is less than the first bin boundary or
            # we couldn't find a bin, the feature is out of bounds
            if bin_index is None:
                return None
            
            bin_indices.append(bin_index)
        
        return tuple(bin_indices)
    
    def add_program(self, program_entry: ProgramEntry, primary_score_key: str) -> bool:
        """
        Add a program to the archive if it outperforms the current elite in its bin.
        
        Args:
            program_entry: The program entry to potentially add to the archive
            primary_score_key: The key in program_entry.scores to use for comparison
            
        Returns:
            True if the program was added to the archive, False otherwise
            
        Raises:
            KeyError: If primary_score_key is not in program_entry.scores
        """
        # Ensure the primary_score_key exists in the program's scores
        if primary_score_key not in program_entry.scores:
            raise KeyError(f"Primary score key '{primary_score_key}' not found in program scores")
        
        # Get the bin key for the program's features
        bin_key = self._get_feature_bin_key(program_entry.features)
        if bin_key is None:
            # Features are out of bounds, program is not added
            return False
        
        # If the bin is empty or the new program is better, add it
        if (bin_key not in self.archive or 
            program_entry.scores[primary_score_key] > self.archive[bin_key].scores[primary_score_key]):
            self.archive[bin_key] = program_entry
            return True
        
        return False
    
    def get_elite(self, features: Tuple) -> Optional[ProgramEntry]:
        """
        Get the elite program for the bin corresponding to the given features.
        
        Args:
            features: The feature values to look up
            
        Returns:
            The elite program entry for the corresponding bin, or None if there
            is no elite for that bin
        """
        bin_key = self._get_feature_bin_key(features)
        if bin_key is None or bin_key not in self.archive:
            return None
        
        return self.archive[bin_key]
    
    def get_random_elites(self, count: int) -> List[ProgramEntry]:
        """
        Get a random selection of elites from the archive.
        
        Args:
            count: The number of random elites to return
            
        Returns:
            A list of up to 'count' random elite program entries. If the archive
            contains fewer than 'count' elites, all available elites are returned.
        """
        elites = list(self.archive.values())
        
        if not elites:
            return []
        
        # If we have fewer elites than requested, return all of them
        if len(elites) <= count:
            return elites
        
        # Otherwise, return a random sample
        return random.sample(elites, count)