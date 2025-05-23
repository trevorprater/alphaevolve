"""
Advanced MAP-Elites variations and adaptive archive implementations.

This module provides sophisticated MAP-Elites variants including CVT-MAP-Elites,
adaptive binning, and other advanced archive management strategies.
"""

import numpy as np
import math
import random
from typing import Dict, List, Tuple, Optional, Any, Union, Protocol
from dataclasses import dataclass, field
from collections import defaultdict
import logging
from abc import ABC, abstractmethod

from alpha_evolve.program_database import ProgramEntry
from alpha_evolve.feature_configuration import FeatureManager, get_feature_manager
from alpha_evolve.diversity_metrics import get_diversity_metric, CompositeDiversityMetric, DiversityScore


@dataclass
class ArchiveCell:
    """
    Represents a single cell in an advanced MAP-Elites archive.
    
    Attributes:
        elite: The best program in this cell
        centroid: Center point of this cell in feature space
        bounds: Boundary definition for this cell
        visit_count: Number of times this cell has been accessed
        quality_history: History of quality scores for this cell
        last_updated: Generation when this cell was last updated
        diversity_scores: History of diversity scores for programs in this cell
        alternative_elites: Alternative programs with high diversity scores
    """
    elite: Optional[ProgramEntry] = None
    centroid: Optional[np.ndarray] = None
    bounds: Optional[Dict[str, Tuple[float, float]]] = None
    visit_count: int = 0
    quality_history: List[float] = field(default_factory=list)
    last_updated: int = 0
    diversity_scores: List[DiversityScore] = field(default_factory=list)
    alternative_elites: List[ProgramEntry] = field(default_factory=list)
    
    def add_quality_score(self, score: float, max_history: int = 100) -> None:
        """Add a quality score to the history, maintaining max length."""
        self.quality_history.append(score)
        if len(self.quality_history) > max_history:
            self.quality_history.pop(0)
    
    def get_quality_trend(self) -> float:
        """Get the trend in quality scores (positive = improving)."""
        if len(self.quality_history) < 2:
            return 0.0
        
        # Simple linear regression slope
        n = len(self.quality_history)
        x_mean = (n - 1) / 2
        y_mean = sum(self.quality_history) / n
        
        numerator = sum((i - x_mean) * (score - y_mean) for i, score in enumerate(self.quality_history))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator > 0 else 0.0
    
    def add_diversity_aware_program(
        self, 
        program_entry: ProgramEntry, 
        diversity_metric: CompositeDiversityMetric,
        max_alternatives: int = 5
    ) -> bool:
        """
        Add a program considering both quality and diversity.
        
        Args:
            program_entry: The program to potentially add
            diversity_metric: Metric for calculating diversity
            max_alternatives: Maximum number of alternative elites to keep
            
        Returns:
            True if the program was added (as elite or alternative)
        """
        # If no elite exists, this becomes the elite
        if self.elite is None:
            self.elite = program_entry
            return True
        
        # Calculate diversity score against current elite
        diversity_score = diversity_metric.calculate_diversity(
            self.elite.code, program_entry.code
        )
        
        # Store diversity score
        self.diversity_scores.append(diversity_score)
        if len(self.diversity_scores) > 100:  # Limit history
            self.diversity_scores.pop(0)
        
        # High diversity threshold for keeping alternatives
        high_diversity_threshold = 0.3
        
        # If highly diverse, consider keeping as alternative
        if diversity_score.total_score > high_diversity_threshold:
            self._add_alternative_elite(program_entry, max_alternatives)
            return True
        
        return False
    
    def _add_alternative_elite(self, program_entry: ProgramEntry, max_alternatives: int) -> None:
        """Add program as an alternative elite with diversity consideration."""
        self.alternative_elites.append(program_entry)
        
        # Maintain maximum number of alternatives
        if len(self.alternative_elites) > max_alternatives:
            # Remove the least diverse alternative
            diversity_metric = get_diversity_metric()
            
            # Calculate diversity scores for all alternatives against the elite
            diversities = []
            for alt in self.alternative_elites:
                div_score = diversity_metric.calculate_diversity(self.elite.code, alt.code)
                diversities.append((div_score.total_score, alt))
            
            # Sort by diversity (ascending) and remove the least diverse
            diversities.sort(key=lambda x: x[0])
            self.alternative_elites = [alt for _, alt in diversities[1:]]
    
    def get_diverse_sample(self, diversity_metric: CompositeDiversityMetric) -> Optional[ProgramEntry]:
        """
        Get a diverse sample from this cell (elite or alternative).
        
        Returns either the elite or a randomly selected alternative that provides good diversity.
        """
        if not self.alternative_elites:
            return self.elite
        
        # Randomly choose between elite and alternatives, weighted by recency
        candidates = [self.elite] + self.alternative_elites
        
        # Simple random selection for now
        return random.choice(candidates)
    
    def get_diversity_statistics(self) -> Dict[str, float]:
        """Get statistics about diversity in this cell."""
        if not self.diversity_scores:
            return {
                'avg_diversity': 0.0,
                'max_diversity': 0.0,
                'diversity_trend': 0.0,
                'alternative_count': len(self.alternative_elites)
            }
        
        total_scores = [ds.total_score for ds in self.diversity_scores]
        
        # Calculate trend in diversity scores
        diversity_trend = 0.0
        if len(total_scores) >= 2:
            n = len(total_scores)
            x_mean = (n - 1) / 2
            y_mean = sum(total_scores) / n
            
            numerator = sum((i - x_mean) * (score - y_mean) for i, score in enumerate(total_scores))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            
            diversity_trend = numerator / denominator if denominator > 0 else 0.0
        
        return {
            'avg_diversity': sum(total_scores) / len(total_scores),
            'max_diversity': max(total_scores),
            'diversity_trend': diversity_trend,
            'alternative_count': len(self.alternative_elites)
        }


class AdvancedArchiveInterface(ABC):
    """Abstract interface for advanced MAP-Elites archive implementations."""
    
    @abstractmethod
    def add_program(self, program_entry: ProgramEntry, primary_score_key: str) -> bool:
        """Add a program to the archive."""
        pass
    
    @abstractmethod
    def get_elite(self, features: Union[Tuple, np.ndarray]) -> Optional[ProgramEntry]:
        """Get the elite program for given features."""
        pass
    
    @abstractmethod
    def get_random_elites(self, count: int) -> List[ProgramEntry]:
        """Get random elite programs from the archive."""
        pass
    
    @abstractmethod
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the archive."""
        pass
    
    @abstractmethod
    def adapt_archive_structure(self, generation: int) -> None:
        """Adapt the archive structure based on current state."""
        pass
    
    @abstractmethod
    def get_diverse_elites(self, count: int, diversity_threshold: float = 0.5) -> List[ProgramEntry]:
        """Get diverse elite programs from the archive."""
        pass
    
    @abstractmethod
    def get_diversity_statistics(self) -> Dict[str, Any]:
        """Get diversity statistics for the archive."""
        pass


class CVTMAPElitesArchive(AdvancedArchiveInterface):
    """
    Centroidal Voronoi Tessellation MAP-Elites archive.
    
    This implements CVT-MAP-Elites which uses Voronoi tessellation to create
    more uniform coverage of the feature space compared to regular grid-based binning.
    """
    
    def __init__(
        self, 
        feature_dimensions: int,
        num_centroids: int = 1000,
        feature_manager: Optional[FeatureManager] = None,
        adaptation_frequency: int = 100
    ):
        """
        Initialize CVT-MAP-Elites archive.
        
        Args:
            feature_dimensions: Number of feature dimensions
            num_centroids: Number of Voronoi centroids
            feature_manager: Feature manager for extracting features
            adaptation_frequency: How often to adapt centroids (in generations)
        """
        self.feature_dimensions = feature_dimensions
        self.num_centroids = num_centroids
        self.feature_manager = feature_manager or get_feature_manager()
        self.adaptation_frequency = adaptation_frequency
        
        # Initialize centroids randomly in unit hypercube
        self.centroids = np.random.random((num_centroids, feature_dimensions))
        
        # Archive cells indexed by centroid index
        self.cells: Dict[int, ArchiveCell] = {
            i: ArchiveCell(centroid=self.centroids[i]) 
            for i in range(num_centroids)
        }
        
        # Track all program features for adaptation
        self.all_features: List[np.ndarray] = []
        self.generation_count = 0
        
        # Diversity metrics
        self.diversity_metric = get_diversity_metric()
        self.enable_diversity_mode = True
        
        self.logger = logging.getLogger(__name__ + ".CVTMAPElitesArchive")
    
    def _normalize_features(self, features: Union[Tuple, np.ndarray, List]) -> np.ndarray:
        """Normalize features to [0, 1] range."""
        if isinstance(features, (tuple, list)):
            features = np.array(features, dtype=float)
        
        # Simple min-max normalization - in practice, would use feature manager bounds
        # For now, assume features are already reasonably normalized
        features = np.clip(features, 0, 1)
        return features
    
    def _find_nearest_centroid(self, features: np.ndarray) -> int:
        """Find the index of the nearest centroid to the given features."""
        features = self._normalize_features(features)
        
        # Calculate Euclidean distances to all centroids
        distances = np.sum((self.centroids - features) ** 2, axis=1)
        return int(np.argmin(distances))
    
    def add_program(self, program_entry: ProgramEntry, primary_score_key: str) -> bool:
        """Add a program to the CVT archive."""
        if primary_score_key not in program_entry.scores:
            raise KeyError(f"Primary score key '{primary_score_key}' not found in program scores")
        
        # Convert features to numpy array
        features = np.array(program_entry.features, dtype=float)
        if len(features) != self.feature_dimensions:
            self.logger.warning(f"Feature dimension mismatch: expected {self.feature_dimensions}, got {len(features)}")
            return False
        
        # Track all features for adaptation
        self.all_features.append(features)
        
        # Find nearest centroid
        centroid_idx = self._find_nearest_centroid(features)
        cell = self.cells[centroid_idx]
        
        # Update cell
        cell.visit_count += 1
        new_score = program_entry.scores[primary_score_key]
        cell.add_quality_score(new_score)
        
        # Check if this is a new elite for this cell
        is_new_elite = False
        if cell.elite is None or new_score > cell.elite.scores[primary_score_key]:
            cell.elite = program_entry
            cell.last_updated = self.generation_count
            self.logger.debug(f"New elite in centroid {centroid_idx} with score {new_score:.4f}")
            is_new_elite = True
        elif self.enable_diversity_mode:
            # Try to add as diverse alternative even if not the best quality
            diversity_added = cell.add_diversity_aware_program(program_entry, self.diversity_metric)
            return diversity_added
        
        return is_new_elite
    
    def get_elite(self, features: Union[Tuple, np.ndarray]) -> Optional[ProgramEntry]:
        """Get the elite program for the cell nearest to given features."""
        features_array = np.array(features, dtype=float)
        centroid_idx = self._find_nearest_centroid(features_array)
        return self.cells[centroid_idx].elite
    
    def get_random_elites(self, count: int) -> List[ProgramEntry]:
        """Get random elite programs from the archive."""
        # Get all non-empty cells
        non_empty_cells = [cell for cell in self.cells.values() if cell.elite is not None]
        
        if not non_empty_cells:
            return []
        
        # Sample randomly
        sample_size = min(count, len(non_empty_cells))
        sampled_cells = random.sample(non_empty_cells, sample_size)
        
        return [cell.elite for cell in sampled_cells]
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the CVT archive."""
        non_empty_cells = [cell for cell in self.cells.values() if cell.elite is not None]
        
        if not non_empty_cells:
            return {
                'total_cells': self.num_centroids,
                'occupied_cells': 0,
                'coverage': 0.0,
                'avg_visits_per_cell': 0.0,
                'quality_distribution': {}
            }
        
        total_visits = sum(cell.visit_count for cell in self.cells.values())
        qualities = [cell.elite.scores.get('fitness', 0.0) for cell in non_empty_cells]
        
        return {
            'total_cells': self.num_centroids,
            'occupied_cells': len(non_empty_cells),
            'coverage': len(non_empty_cells) / self.num_centroids,
            'avg_visits_per_cell': total_visits / self.num_centroids,
            'quality_distribution': {
                'mean': np.mean(qualities) if qualities else 0.0,
                'std': np.std(qualities) if qualities else 0.0,
                'min': np.min(qualities) if qualities else 0.0,
                'max': np.max(qualities) if qualities else 0.0
            },
            'centroid_adaptation_count': getattr(self, '_adaptation_count', 0)
        }
    
    def adapt_archive_structure(self, generation: int) -> None:
        """Adapt centroid positions based on the distribution of evaluated programs."""
        self.generation_count = generation
        
        if generation % self.adaptation_frequency != 0 or len(self.all_features) < self.num_centroids:
            return
        
        self.logger.info(f"Adapting CVT centroids at generation {generation}")
        
        # Perform k-means clustering on all observed features
        self._adapt_centroids_kmeans()
        
        # Update adaptation count
        if not hasattr(self, '_adaptation_count'):
            self._adaptation_count = 0
        self._adaptation_count += 1
        
        # Clear feature history to prevent memory growth
        self.all_features = self.all_features[-1000:]  # Keep only recent features
    
    def _adapt_centroids_kmeans(self, max_iterations: int = 50) -> None:
        """Adapt centroids using k-means clustering on observed features."""
        if len(self.all_features) < self.num_centroids:
            return
        
        features_array = np.array(self.all_features)
        features_array = np.array([self._normalize_features(f) for f in features_array])
        
        # Initialize centroids with current positions
        new_centroids = self.centroids.copy()
        
        for iteration in range(max_iterations):
            # Assign each feature to nearest centroid
            assignments = []
            for feature in features_array:
                distances = np.sum((new_centroids - feature) ** 2, axis=1)
                assignments.append(np.argmin(distances))
            
            # Update centroids to cluster means
            old_centroids = new_centroids.copy()
            
            for i in range(self.num_centroids):
                cluster_features = features_array[np.array(assignments) == i]
                if len(cluster_features) > 0:
                    new_centroids[i] = np.mean(cluster_features, axis=0)
            
            # Check for convergence
            centroid_movement = np.mean(np.sum((new_centroids - old_centroids) ** 2, axis=1))
            if centroid_movement < 1e-6:
                break
        
        # Update centroids and cell centroids
        self.centroids = new_centroids
        for i, cell in self.cells.items():
            cell.centroid = self.centroids[i]
        
        self.logger.debug(f"Centroid adaptation completed in {iteration + 1} iterations")
    
    def get_diverse_elites(self, count: int, diversity_threshold: float = 0.5) -> List[ProgramEntry]:
        """Get diverse elite programs from the archive."""
        if not self.enable_diversity_mode:
            return self.get_random_elites(count)
        
        # Get all non-empty cells
        non_empty_cells = [cell for cell in self.cells.values() if cell.elite is not None]
        
        if not non_empty_cells:
            return []
        
        selected_programs = []
        
        # Start with the best program overall
        best_cell = max(non_empty_cells, key=lambda c: max(c.elite.scores.values()))
        selected_programs.append(best_cell.get_diverse_sample(self.diversity_metric))
        
        # Greedily select diverse programs
        while len(selected_programs) < count and len(selected_programs) < len(non_empty_cells):
            best_candidate = None
            best_diversity = -1
            
            for cell in non_empty_cells:
                candidate = cell.get_diverse_sample(self.diversity_metric)
                
                # Skip if already selected
                if candidate in selected_programs:
                    continue
                
                # Calculate minimum diversity to already selected programs
                min_diversity = float('inf')
                for selected in selected_programs:
                    div_score = self.diversity_metric.calculate_diversity(
                        candidate.code, selected.code
                    )
                    min_diversity = min(min_diversity, div_score.total_score)
                
                # Select candidate with highest minimum diversity
                if min_diversity > best_diversity and min_diversity >= diversity_threshold:
                    best_diversity = min_diversity
                    best_candidate = candidate
            
            if best_candidate is None:
                # Fallback to random selection if no diverse candidates found
                remaining_cells = [c for c in non_empty_cells 
                                 if c.get_diverse_sample(self.diversity_metric) not in selected_programs]
                if remaining_cells:
                    random_cell = random.choice(remaining_cells)
                    selected_programs.append(random_cell.get_diverse_sample(self.diversity_metric))
                else:
                    break
            else:
                selected_programs.append(best_candidate)
        
        return selected_programs
    
    def get_diversity_statistics(self) -> Dict[str, Any]:
        """Get diversity statistics for the CVT archive."""
        non_empty_cells = [cell for cell in self.cells.values() if cell.elite is not None]
        
        if not non_empty_cells:
            return {
                'avg_diversity_per_cell': 0.0,
                'max_diversity_per_cell': 0.0,
                'total_alternative_elites': 0,
                'cells_with_alternatives': 0,
                'archive_diversity_score': 0.0
            }
        
        # Calculate cell-level diversity statistics
        cell_diversity_stats = [cell.get_diversity_statistics() for cell in non_empty_cells]
        
        avg_cell_diversity = np.mean([stats['avg_diversity'] for stats in cell_diversity_stats])
        max_cell_diversity = np.max([stats['max_diversity'] for stats in cell_diversity_stats])
        total_alternatives = sum(stats['alternative_count'] for stats in cell_diversity_stats)
        cells_with_alternatives = sum(1 for stats in cell_diversity_stats if stats['alternative_count'] > 0)
        
        # Calculate overall archive diversity (sample-based)
        archive_diversity = self._calculate_archive_diversity_sample()
        
        return {
            'avg_diversity_per_cell': avg_cell_diversity,
            'max_diversity_per_cell': max_cell_diversity,
            'total_alternative_elites': total_alternatives,
            'cells_with_alternatives': cells_with_alternatives,
            'archive_diversity_score': archive_diversity,
            'diversity_mode_enabled': self.enable_diversity_mode
        }
    
    def _calculate_archive_diversity_sample(self, sample_size: int = 50) -> float:
        """Calculate overall archive diversity using a sample of programs."""
        elites = self.get_random_elites(min(sample_size, self.num_centroids))
        
        if len(elites) < 2:
            return 0.0
        
        # Calculate pairwise diversities
        diversities = []
        for i in range(len(elites)):
            for j in range(i + 1, len(elites)):
                div_score = self.diversity_metric.calculate_diversity(
                    elites[i].code, elites[j].code
                )
                diversities.append(div_score.total_score)
        
        return np.mean(diversities) if diversities else 0.0
    
    def set_diversity_mode(self, enabled: bool) -> None:
        """Enable or disable diversity-aware mode."""
        self.enable_diversity_mode = enabled
        self.logger.info(f"Diversity mode {'enabled' if enabled else 'disabled'}")
    
    def get_diversity_mode(self) -> bool:
        """Check if diversity mode is enabled."""
        return self.enable_diversity_mode


class AdaptiveMAPElitesArchive(AdvancedArchiveInterface):
    """
    Adaptive MAP-Elites archive with dynamic binning.
    
    This archive adapts its binning structure based on the distribution of
    programs and their performance, allowing for more fine-grained exploration
    of promising regions of the feature space.
    """
    
    def __init__(
        self,
        initial_bins_per_dimension: int = 10,
        max_bins_per_dimension: int = 50,
        feature_manager: Optional[FeatureManager] = None,
        adaptation_threshold: int = 100,
        split_threshold: float = 0.8
    ):
        """
        Initialize adaptive MAP-Elites archive.
        
        Args:
            initial_bins_per_dimension: Initial number of bins per dimension
            max_bins_per_dimension: Maximum allowed bins per dimension
            feature_manager: Feature manager for extracting features
            adaptation_threshold: Minimum programs before adapting
            split_threshold: Quality threshold for splitting bins
        """
        self.initial_bins = initial_bins_per_dimension
        self.max_bins = max_bins_per_dimension
        self.feature_manager = feature_manager or get_feature_manager()
        self.adaptation_threshold = adaptation_threshold
        self.split_threshold = split_threshold
        
        # Current binning structure
        self.feature_names = self.feature_manager.get_enabled_features()
        self.num_dimensions = len(self.feature_names)
        
        # Initialize with uniform binning
        self.bin_boundaries = self._initialize_uniform_binning()
        
        # Archive cells indexed by bin coordinates
        self.cells: Dict[Tuple[int, ...], ArchiveCell] = {}
        
        # Track programs for adaptation
        self.program_count = 0
        self.adaptation_count = 0
        
        self.logger = logging.getLogger(__name__ + ".AdaptiveMAPElitesArchive")
    
    def _initialize_uniform_binning(self) -> Dict[str, List[float]]:
        """Initialize uniform binning for all features."""
        boundaries = {}
        
        for feature_name in self.feature_names:
            # Get feature configuration
            feature_config = self.feature_manager.features.get(feature_name)
            if feature_config:
                try:
                    feature_boundaries = feature_config.get_bin_boundaries()
                    if len(feature_boundaries) >= 2:
                        boundaries[feature_name] = feature_boundaries
                    else:
                        # Fallback to default if boundaries are invalid
                        boundaries[feature_name] = [i / self.initial_bins for i in range(self.initial_bins + 1)]
                except Exception as e:
                    self.logger.warning(f"Failed to get boundaries for feature '{feature_name}': {e}")
                    boundaries[feature_name] = [i / self.initial_bins for i in range(self.initial_bins + 1)]
            else:
                # Default uniform binning
                boundaries[feature_name] = [i / self.initial_bins for i in range(self.initial_bins + 1)]
        
        return boundaries
    
    def _get_bin_coordinates(self, features: Union[Tuple, List, Dict]) -> Optional[Tuple[int, ...]]:
        """Convert feature values to bin coordinates."""
        if isinstance(features, (tuple, list)):
            if len(features) != self.num_dimensions:
                return None
            feature_dict = dict(zip(self.feature_names, features))
        elif isinstance(features, dict):
            feature_dict = features
        else:
            return None
        
        coordinates = []
        
        for feature_name in self.feature_names:
            if feature_name not in feature_dict:
                return None
            
            value = feature_dict[feature_name]
            boundaries = self.bin_boundaries.get(feature_name, [])
            
            # Check if boundaries exist and are valid
            if len(boundaries) < 2:
                self.logger.warning(f"Invalid boundaries for feature '{feature_name}': {boundaries}")
                return None
            
            # Find bin index
            bin_index = None
            for i in range(len(boundaries) - 1):
                if boundaries[i] <= value < boundaries[i + 1]:
                    bin_index = i
                    break
            
            # Handle edge case where value equals the last boundary
            if bin_index is None and value >= boundaries[-1]:
                bin_index = len(boundaries) - 2
            
            if bin_index is None:
                # Value is out of bounds, use closest bin
                if value < boundaries[0]:
                    bin_index = 0
                else:
                    bin_index = len(boundaries) - 2
            
            coordinates.append(bin_index)
        
        return tuple(coordinates)
    
    def add_program(self, program_entry: ProgramEntry, primary_score_key: str) -> bool:
        """Add a program to the adaptive archive."""
        if primary_score_key not in program_entry.scores:
            raise KeyError(f"Primary score key '{primary_score_key}' not found in program scores")
        
        # Extract features using feature manager
        features = self.feature_manager.extract_features(program_entry.code)
        
        # Get bin coordinates
        bin_coords = self._get_bin_coordinates(features)
        if bin_coords is None:
            return False
        
        # Get or create cell
        if bin_coords not in self.cells:
            self.cells[bin_coords] = ArchiveCell()
        
        cell = self.cells[bin_coords]
        
        # Update cell
        cell.visit_count += 1
        new_score = program_entry.scores[primary_score_key]
        cell.add_quality_score(new_score)
        
        # Check if this is a new elite
        if cell.elite is None or new_score > cell.elite.scores[primary_score_key]:
            cell.elite = program_entry
            cell.last_updated = self.program_count
            
            self.program_count += 1
            
            # Check if we should adapt the archive
            if self.program_count % self.adaptation_threshold == 0:
                self.adapt_archive_structure(self.program_count // self.adaptation_threshold)
            
            return True
        
        self.program_count += 1
        return False
    
    def get_elite(self, features: Union[Tuple, np.ndarray]) -> Optional[ProgramEntry]:
        """Get the elite program for given features."""
        bin_coords = self._get_bin_coordinates(features)
        if bin_coords is None or bin_coords not in self.cells:
            return None
        
        return self.cells[bin_coords].elite
    
    def get_random_elites(self, count: int) -> List[ProgramEntry]:
        """Get random elite programs from the archive."""
        non_empty_cells = [cell for cell in self.cells.values() if cell.elite is not None]
        
        if not non_empty_cells:
            return []
        
        sample_size = min(count, len(non_empty_cells))
        sampled_cells = random.sample(non_empty_cells, sample_size)
        
        return [cell.elite for cell in sampled_cells]
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the adaptive archive."""
        non_empty_cells = [cell for cell in self.cells.values() if cell.elite is not None]
        
        # Calculate total possible cells
        total_possible_cells = 1
        for boundaries in self.bin_boundaries.values():
            total_possible_cells *= (len(boundaries) - 1)
        
        if not non_empty_cells:
            return {
                'total_possible_cells': total_possible_cells,
                'occupied_cells': 0,
                'coverage': 0.0,
                'adaptation_count': self.adaptation_count,
                'bins_per_dimension': {name: len(boundaries) - 1 for name, boundaries in self.bin_boundaries.items()}
            }
        
        qualities = [cell.elite.scores.get('fitness', 0.0) for cell in non_empty_cells]
        
        return {
            'total_possible_cells': total_possible_cells,
            'occupied_cells': len(non_empty_cells),
            'coverage': len(non_empty_cells) / total_possible_cells if total_possible_cells > 0 else 0.0,
            'adaptation_count': self.adaptation_count,
            'bins_per_dimension': {name: len(boundaries) - 1 for name, boundaries in self.bin_boundaries.items()},
            'quality_distribution': {
                'mean': np.mean(qualities),
                'std': np.std(qualities),
                'min': np.min(qualities),
                'max': np.max(qualities)
            }
        }
    
    def adapt_archive_structure(self, generation: int) -> None:
        """Adapt the binning structure based on current archive state."""
        self.logger.info(f"Adapting archive structure at generation {generation}")
        
        # Find high-performing regions that could benefit from finer binning
        high_quality_cells = []
        
        for coords, cell in self.cells.items():
            if cell.elite is not None:
                # Check if this cell has high quality and activity
                quality = cell.elite.scores.get('fitness', 0.0)
                quality_trend = cell.get_quality_trend()
                
                if quality > self.split_threshold or quality_trend > 0.1:
                    high_quality_cells.append((coords, cell, quality))
        
        # Sort by quality
        high_quality_cells.sort(key=lambda x: x[2], reverse=True)
        
        # Attempt to split the top cells
        splits_performed = 0
        max_splits_per_adaptation = 3  # Limit splits to prevent explosion
        
        for coords, cell, quality in high_quality_cells[:max_splits_per_adaptation]:
            if self._attempt_bin_split(coords):
                splits_performed += 1
        
        if splits_performed > 0:
            self.adaptation_count += 1
            self.logger.info(f"Performed {splits_performed} bin splits")
        else:
            self.logger.debug("No bins were split in this adaptation")
    
    def _attempt_bin_split(self, bin_coords: Tuple[int, ...]) -> bool:
        """Attempt to split a bin along its largest dimension."""
        # Find the feature dimension with the largest bin size
        best_dimension = None
        largest_bin_size = 0
        
        for i, feature_name in enumerate(self.feature_names):
            boundaries = self.bin_boundaries[feature_name]
            
            # Check if we can split (not at max bins)
            if len(boundaries) - 1 >= self.max_bins:
                continue
            
            # Get current bin size
            bin_idx = bin_coords[i]
            if bin_idx < len(boundaries) - 1:
                bin_size = boundaries[bin_idx + 1] - boundaries[bin_idx]
                if bin_size > largest_bin_size:
                    largest_bin_size = bin_size
                    best_dimension = i
        
        if best_dimension is None:
            return False  # No dimension can be split
        
        # Split the chosen dimension
        feature_name = self.feature_names[best_dimension]
        boundaries = self.bin_boundaries[feature_name]
        bin_idx = bin_coords[best_dimension]
        
        # Insert new boundary at midpoint
        midpoint = (boundaries[bin_idx] + boundaries[bin_idx + 1]) / 2
        new_boundaries = boundaries[:bin_idx + 1] + [midpoint] + boundaries[bin_idx + 1:]
        
        self.bin_boundaries[feature_name] = new_boundaries
        
        # Note: In a full implementation, we would need to:
        # 1. Redistribute existing programs to new bins
        # 2. Update all bin coordinates
        # For now, we just update the boundaries
        
        self.logger.debug(f"Split dimension {feature_name} at bin {bin_idx}, new midpoint: {midpoint:.4f}")
        return True
    
    def get_diverse_elites(self, count: int, diversity_threshold: float = 0.5) -> List[ProgramEntry]:
        """Get diverse elite programs from the adaptive archive."""
        # Simple implementation - get random elites
        # In a full implementation, would use diversity metrics
        return self.get_random_elites(count)
    
    def get_diversity_statistics(self) -> Dict[str, Any]:
        """Get diversity statistics for the adaptive archive."""
        non_empty_cells = [cell for cell in self.cells.values() if cell.elite is not None]
        
        return {
            'total_cells': len(self.cells),
            'occupied_cells': len(non_empty_cells),
            'avg_diversity_per_cell': 0.0,  # Placeholder
            'max_diversity_per_cell': 0.0,  # Placeholder
            'archive_diversity_score': 0.0,  # Placeholder
            'diversity_mode_enabled': False  # Not implemented for adaptive archive
        }


class HierarchicalMAPElitesArchive(AdvancedArchiveInterface):
    """
    Hierarchical MAP-Elites archive with multi-resolution exploration.
    
    This archive maintains multiple resolution levels, allowing for both
    broad exploration and fine-grained optimization.
    """
    
    def __init__(
        self,
        feature_manager: Optional[FeatureManager] = None,
        resolution_levels: List[int] = None,
        promotion_threshold: float = 0.8
    ):
        """
        Initialize hierarchical MAP-Elites archive.
        
        Args:
            feature_manager: Feature manager for extracting features
            resolution_levels: List of bin counts for each resolution level
            promotion_threshold: Quality threshold for promotion to higher resolution
        """
        self.feature_manager = feature_manager or get_feature_manager()
        self.resolution_levels = resolution_levels or [5, 10, 20]
        self.promotion_threshold = promotion_threshold
        
        # Create archives for each resolution level
        self.archives: List[AdaptiveMAPElitesArchive] = []
        
        for resolution in self.resolution_levels:
            archive = AdaptiveMAPElitesArchive(
                initial_bins_per_dimension=resolution,
                max_bins_per_dimension=resolution * 2,
                feature_manager=self.feature_manager
            )
            self.archives.append(archive)
        
        self.program_count = 0
        self.logger = logging.getLogger(__name__ + ".HierarchicalMAPElitesArchive")
    
    def add_program(self, program_entry: ProgramEntry, primary_score_key: str) -> bool:
        """Add a program to the hierarchical archive."""
        quality = program_entry.scores.get(primary_score_key, 0.0)
        
        # Always add to lowest resolution
        added_to_any = self.archives[0].add_program(program_entry, primary_score_key)
        
        # Promote to higher resolutions based on quality
        for i, archive in enumerate(self.archives[1:], 1):
            # Only promote if quality is above threshold
            level_threshold = self.promotion_threshold * (i / len(self.archives))
            
            if quality >= level_threshold:
                archive_added = archive.add_program(program_entry, primary_score_key)
                added_to_any = added_to_any or archive_added
        
        self.program_count += 1
        return added_to_any
    
    def get_elite(self, features: Union[Tuple, np.ndarray]) -> Optional[ProgramEntry]:
        """Get the elite program from the highest resolution archive that has it."""
        # Search from highest to lowest resolution
        for archive in reversed(self.archives):
            elite = archive.get_elite(features)
            if elite is not None:
                return elite
        
        return None
    
    def get_random_elites(self, count: int) -> List[ProgramEntry]:
        """Get random elites from all resolution levels."""
        all_elites = []
        
        # Collect elites from all levels
        for archive in self.archives:
            level_elites = archive.get_random_elites(count)
            all_elites.extend(level_elites)
        
        # Remove duplicates (by ID) and sample
        unique_elites = {}
        for elite in all_elites:
            unique_elites[elite.id] = elite
        
        unique_list = list(unique_elites.values())
        
        if len(unique_list) <= count:
            return unique_list
        
        return random.sample(unique_list, count)
    
    def get_archive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the hierarchical archive."""
        level_stats = []
        
        for i, archive in enumerate(self.archives):
            stats = archive.get_archive_stats()
            stats['resolution_level'] = self.resolution_levels[i]
            level_stats.append(stats)
        
        return {
            'total_programs': self.program_count,
            'resolution_levels': self.resolution_levels,
            'level_statistics': level_stats,
            'promotion_threshold': self.promotion_threshold
        }
    
    def adapt_archive_structure(self, generation: int) -> None:
        """Adapt all resolution levels."""
        for archive in self.archives:
            archive.adapt_archive_structure(generation)
    
    def get_diverse_elites(self, count: int, diversity_threshold: float = 0.5) -> List[ProgramEntry]:
        """Get diverse elite programs from the hierarchical archive."""
        # Simple implementation - get random elites from highest resolution
        # In a full implementation, would use diversity metrics across all levels
        if self.archives:
            return self.archives[-1].get_random_elites(count)
        return []
    
    def get_diversity_statistics(self) -> Dict[str, Any]:
        """Get diversity statistics for the hierarchical archive."""
        total_cells = sum(len(archive.cells) for archive in self.archives)
        occupied_cells = sum(len([cell for cell in archive.cells.values() if cell.elite is not None]) 
                           for archive in self.archives)
        
        return {
            'total_cells': total_cells,
            'occupied_cells': occupied_cells,
            'resolution_levels': len(self.archives),
            'avg_diversity_per_cell': 0.0,  # Placeholder
            'max_diversity_per_cell': 0.0,  # Placeholder
            'archive_diversity_score': 0.0,  # Placeholder
            'diversity_mode_enabled': False  # Not implemented for hierarchical archive
        }


def create_advanced_archive(
    archive_type: str = 'cvt',
    feature_manager: Optional[FeatureManager] = None,
    **kwargs
) -> AdvancedArchiveInterface:
    """
    Factory function to create advanced MAP-Elites archives.
    
    Args:
        archive_type: Type of archive ('cvt', 'adaptive', 'hierarchical')
        feature_manager: Feature manager instance
        **kwargs: Additional arguments for specific archive types
    
    Returns:
        Configured advanced archive instance
    """
    if archive_type == 'cvt':
        return CVTMAPElitesArchive(
            feature_dimensions=kwargs.get('feature_dimensions', 2),
            num_centroids=kwargs.get('num_centroids', 1000),
            feature_manager=feature_manager,
            adaptation_frequency=kwargs.get('adaptation_frequency', 100)
        )
    elif archive_type == 'adaptive':
        return AdaptiveMAPElitesArchive(
            initial_bins_per_dimension=kwargs.get('initial_bins', 10),
            max_bins_per_dimension=kwargs.get('max_bins', 50),
            feature_manager=feature_manager,
            adaptation_threshold=kwargs.get('adaptation_threshold', 100),
            split_threshold=kwargs.get('split_threshold', 0.8)
        )
    elif archive_type == 'hierarchical':
        return HierarchicalMAPElitesArchive(
            feature_manager=feature_manager,
            resolution_levels=kwargs.get('resolution_levels', [5, 10, 20]),
            promotion_threshold=kwargs.get('promotion_threshold', 0.8)
        )
    else:
        raise ValueError(f"Unknown archive type: {archive_type}")


class ArchiveComparison:
    """Utility class for comparing different archive implementations."""
    
    @staticmethod
    def run_comparison(
        archives: Dict[str, AdvancedArchiveInterface],
        test_programs: List[ProgramEntry],
        primary_score_key: str = 'fitness'
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare multiple archive implementations on the same set of programs.
        
        Args:
            archives: Dictionary mapping archive names to archive instances
            test_programs: List of programs to add to each archive
            primary_score_key: Score key to use for comparisons
        
        Returns:
            Dictionary containing comparison results
        """
        results = {}
        
        for archive_name, archive in archives.items():
            # Reset archive state
            archive_copy = type(archive).__new__(type(archive))
            archive_copy.__dict__.update(archive.__dict__)
            
            # Add all programs
            additions = 0
            for program in test_programs:
                if archive_copy.add_program(program, primary_score_key):
                    additions += 1
            
            # Get final statistics
            stats = archive_copy.get_archive_stats()
            stats['programs_added'] = additions
            stats['addition_rate'] = additions / len(test_programs)
            
            results[archive_name] = stats
        
        return results