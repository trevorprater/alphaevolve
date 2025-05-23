"""
Sophisticated diversity metrics for MAP-Elites archives in AlphaEvolve.

This module provides nuanced diversity measures that go beyond basic edit distance,
including semantic similarity, behavioral diversity, and structural comparison metrics.
"""

import ast
import difflib
import math
import numpy as np
from typing import Dict, Any, List, Tuple, Set, Optional, Union, Callable
from dataclasses import dataclass
from collections import defaultdict, Counter
import logging
import hashlib
from abc import ABC, abstractmethod

from .feature_extraction import get_feature_extractor, AdvancedFeatureExtractor


@dataclass
class DiversityScore:
    """
    Container for diversity score with detailed breakdown.
    
    Attributes:
        total_score: Overall diversity score between 0.0 and 1.0
        semantic_score: Semantic similarity component
        behavioral_score: Behavioral diversity component
        structural_score: Structural difference component
        textual_score: Textual difference component
        metadata: Additional information about the comparison
    """
    total_score: float
    semantic_score: float
    behavioral_score: float
    structural_score: float
    textual_score: float
    metadata: Dict[str, Any]


class DiversityMetric(ABC):
    """Abstract base class for diversity metrics."""
    
    @abstractmethod
    def calculate_diversity(self, code1: str, code2: str) -> float:
        """
        Calculate diversity between two code samples.
        
        Args:
            code1: First code sample
            code2: Second code sample
            
        Returns:
            Diversity score between 0.0 (identical) and 1.0 (maximally different)
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of this diversity metric."""
        pass


class SemanticSimilarityMetric(DiversityMetric):
    """
    Measures semantic similarity using AST structure comparison.
    
    This metric analyzes the structural similarity of Abstract Syntax Trees
    to determine how semantically similar two code pieces are.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".SemanticSimilarityMetric")
    
    def calculate_diversity(self, code1: str, code2: str) -> float:
        """Calculate semantic diversity based on AST structure comparison."""
        try:
            tree1 = ast.parse(code1)
            tree2 = ast.parse(code2)
            
            # Extract AST signatures for comparison
            sig1 = self._extract_ast_signature(tree1)
            sig2 = self._extract_ast_signature(tree2)
            
            # Calculate structural similarity
            similarity = self._calculate_structure_similarity(sig1, sig2)
            
            # Return diversity (1 - similarity)
            return 1.0 - similarity
            
        except SyntaxError:
            # If either code has syntax errors, fall back to textual comparison
            return self._textual_fallback_diversity(code1, code2)
        except Exception as e:
            self.logger.warning(f"Error in semantic analysis: {e}")
            return self._textual_fallback_diversity(code1, code2)
    
    def _extract_ast_signature(self, tree: ast.AST) -> Dict[str, Any]:
        """Extract a signature representing the AST structure."""
        signature = {
            'node_types': self._count_node_types(tree),
            'tree_shape': self._extract_tree_shape(tree),
            'function_signatures': self._extract_function_signatures(tree),
            'class_signatures': self._extract_class_signatures(tree),
            'control_flow_patterns': self._extract_control_flow_patterns(tree),
            'import_patterns': self._extract_import_patterns(tree)
        }
        return signature
    
    def _count_node_types(self, tree: ast.AST) -> Dict[str, int]:
        """Count occurrences of each AST node type."""
        counts = defaultdict(int)
        for node in ast.walk(tree):
            counts[type(node).__name__] += 1
        return dict(counts)
    
    def _extract_tree_shape(self, tree: ast.AST) -> List[int]:
        """Extract the shape of the AST tree as a list of depths."""
        def get_depths(node, current_depth=0):
            depths = [current_depth]
            for child in ast.iter_child_nodes(node):
                depths.extend(get_depths(child, current_depth + 1))
            return depths
        
        depths = get_depths(tree)
        # Create a histogram of depths
        max_depth = max(depths) if depths else 0
        shape = [0] * (max_depth + 1)
        for depth in depths:
            shape[depth] += 1
        return shape
    
    def _extract_function_signatures(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract signatures of function definitions."""
        signatures = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                sig = {
                    'name': node.name,
                    'arg_count': len(node.args.args),
                    'has_defaults': len(node.args.defaults) > 0,
                    'has_varargs': node.args.vararg is not None,
                    'has_kwargs': node.args.kwarg is not None,
                    'decorator_count': len(node.decorator_list),
                    'return_annotation': node.returns is not None,
                    'is_async': isinstance(node, ast.AsyncFunctionDef)
                }
                signatures.append(sig)
        
        return signatures
    
    def _extract_class_signatures(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract signatures of class definitions."""
        signatures = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
                sig = {
                    'name': node.name,
                    'base_count': len(node.bases),
                    'method_count': len(methods),
                    'decorator_count': len(node.decorator_list),
                    'has_init': any(m.name == '__init__' for m in methods),
                    'has_str': any(m.name == '__str__' for m in methods)
                }
                signatures.append(sig)
        
        return signatures
    
    def _extract_control_flow_patterns(self, tree: ast.AST) -> Dict[str, int]:
        """Extract control flow patterns."""
        patterns = defaultdict(int)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                patterns['if_statements'] += 1
                if node.orelse:
                    if isinstance(node.orelse[0], ast.If):
                        patterns['elif_chains'] += 1
                    else:
                        patterns['else_blocks'] += 1
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                patterns['for_loops'] += 1
                if node.orelse:
                    patterns['for_else'] += 1
            elif isinstance(node, ast.While):
                patterns['while_loops'] += 1
                if node.orelse:
                    patterns['while_else'] += 1
            elif isinstance(node, ast.Try):
                patterns['try_blocks'] += 1
            elif isinstance(node, ast.ExceptHandler):
                patterns['except_handlers'] += 1
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                patterns['with_statements'] += 1
        
        return dict(patterns)
    
    def _extract_import_patterns(self, tree: ast.AST) -> Dict[str, Any]:
        """Extract import patterns."""
        imports = {'modules': set(), 'from_imports': set(), 'aliases': set()}
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports['modules'].add(alias.name)
                    if alias.asname:
                        imports['aliases'].add(alias.asname)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports['from_imports'].add(node.module)
                for alias in node.names:
                    if alias.asname:
                        imports['aliases'].add(alias.asname)
        
        return {
            'module_count': len(imports['modules']),
            'from_import_count': len(imports['from_imports']),
            'alias_count': len(imports['aliases']),
            'total_imports': len(imports['modules']) + len(imports['from_imports'])
        }
    
    def _calculate_structure_similarity(self, sig1: Dict[str, Any], sig2: Dict[str, Any]) -> float:
        """Calculate structural similarity between two AST signatures."""
        similarities = []
        
        # Node type similarity
        node_sim = self._calculate_dict_similarity(sig1['node_types'], sig2['node_types'])
        similarities.append(('node_types', node_sim, 0.3))
        
        # Tree shape similarity
        shape_sim = self._calculate_list_similarity(sig1['tree_shape'], sig2['tree_shape'])
        similarities.append(('tree_shape', shape_sim, 0.2))
        
        # Function signature similarity
        func_sim = self._calculate_function_similarity(sig1['function_signatures'], sig2['function_signatures'])
        similarities.append(('functions', func_sim, 0.2))
        
        # Class signature similarity
        class_sim = self._calculate_class_similarity(sig1['class_signatures'], sig2['class_signatures'])
        similarities.append(('classes', class_sim, 0.1))
        
        # Control flow similarity
        control_sim = self._calculate_dict_similarity(sig1['control_flow_patterns'], sig2['control_flow_patterns'])
        similarities.append(('control_flow', control_sim, 0.1))
        
        # Import similarity
        import_sim = self._calculate_dict_similarity(sig1['import_patterns'], sig2['import_patterns'])
        similarities.append(('imports', import_sim, 0.1))
        
        # Calculate weighted average
        total_weight = sum(weight for _, _, weight in similarities)
        weighted_sum = sum(sim * weight for _, sim, weight in similarities)
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _calculate_dict_similarity(self, dict1: Dict, dict2: Dict) -> float:
        """Calculate similarity between two dictionaries with numeric values."""
        all_keys = set(dict1.keys()) | set(dict2.keys())
        if not all_keys:
            return 1.0
        
        total_diff = 0.0
        max_possible_diff = 0.0
        
        for key in all_keys:
            val1 = dict1.get(key, 0)
            val2 = dict2.get(key, 0)
            total_diff += abs(val1 - val2)
            max_possible_diff += max(val1, val2)
        
        if max_possible_diff == 0:
            return 1.0
        
        return 1.0 - (total_diff / max_possible_diff)
    
    def _calculate_list_similarity(self, list1: List, list2: List) -> float:
        """Calculate similarity between two lists of numbers."""
        max_len = max(len(list1), len(list2))
        if max_len == 0:
            return 1.0
        
        # Pad shorter list with zeros
        padded1 = list1 + [0] * (max_len - len(list1))
        padded2 = list2 + [0] * (max_len - len(list2))
        
        # Calculate normalized difference
        total_diff = sum(abs(a - b) for a, b in zip(padded1, padded2))
        max_possible_diff = sum(max(a, b) for a, b in zip(padded1, padded2))
        
        if max_possible_diff == 0:
            return 1.0
        
        return 1.0 - (total_diff / max_possible_diff)
    
    def _calculate_function_similarity(self, funcs1: List[Dict], funcs2: List[Dict]) -> float:
        """Calculate similarity between function signatures."""
        if not funcs1 and not funcs2:
            return 1.0
        if not funcs1 or not funcs2:
            return 0.0
        
        # Create simplified signatures for comparison
        sigs1 = [self._simplify_function_signature(f) for f in funcs1]
        sigs2 = [self._simplify_function_signature(f) for f in funcs2]
        
        # Find best matches using Jaccard similarity
        similarities = []
        for sig1 in sigs1:
            best_match = max(sigs2, key=lambda sig2: self._signature_jaccard_similarity(sig1, sig2))
            similarities.append(self._signature_jaccard_similarity(sig1, best_match))
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _calculate_class_similarity(self, classes1: List[Dict], classes2: List[Dict]) -> float:
        """Calculate similarity between class signatures."""
        if not classes1 and not classes2:
            return 1.0
        if not classes1 or not classes2:
            return 0.0
        
        # Similar approach to function similarity
        sigs1 = [self._simplify_class_signature(c) for c in classes1]
        sigs2 = [self._simplify_class_signature(c) for c in classes2]
        
        similarities = []
        for sig1 in sigs1:
            best_match = max(sigs2, key=lambda sig2: self._signature_jaccard_similarity(sig1, sig2))
            similarities.append(self._signature_jaccard_similarity(sig1, best_match))
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _simplify_function_signature(self, func: Dict[str, Any]) -> Set[str]:
        """Convert function signature to a set of features for comparison."""
        features = set()
        features.add(f"args_{func['arg_count']}")
        if func['has_defaults']:
            features.add("has_defaults")
        if func['has_varargs']:
            features.add("has_varargs")
        if func['has_kwargs']:
            features.add("has_kwargs")
        if func['decorator_count'] > 0:
            features.add("has_decorators")
        if func['return_annotation']:
            features.add("has_return_annotation")
        if func['is_async']:
            features.add("is_async")
        return features
    
    def _simplify_class_signature(self, cls: Dict[str, Any]) -> Set[str]:
        """Convert class signature to a set of features for comparison."""
        features = set()
        features.add(f"methods_{cls['method_count']}")
        features.add(f"bases_{cls['base_count']}")
        if cls['decorator_count'] > 0:
            features.add("has_decorators")
        if cls['has_init']:
            features.add("has_init")
        if cls['has_str']:
            features.add("has_str")
        return features
    
    def _signature_jaccard_similarity(self, sig1: Set[str], sig2: Set[str]) -> float:
        """Calculate Jaccard similarity between two signature sets."""
        intersection = len(sig1 & sig2)
        union = len(sig1 | sig2)
        return intersection / union if union > 0 else 0.0
    
    def _textual_fallback_diversity(self, code1: str, code2: str) -> float:
        """Fallback to textual diversity when AST analysis fails."""
        similarity = difflib.SequenceMatcher(None, code1, code2).ratio()
        return 1.0 - similarity
    
    def get_name(self) -> str:
        return "semantic_similarity"


class BehavioralDiversityMetric(DiversityMetric):
    """
    Measures behavioral diversity based on execution patterns and complexity.
    
    This metric analyzes how different the execution behavior of two code pieces
    would be, considering complexity, control flow, and algorithmic patterns.
    """
    
    def __init__(self):
        self.feature_extractor = get_feature_extractor()
        self.logger = logging.getLogger(__name__ + ".BehavioralDiversityMetric")
    
    def calculate_diversity(self, code1: str, code2: str) -> float:
        """Calculate behavioral diversity based on execution characteristics."""
        try:
            # Extract behavioral features from both code samples
            features1 = self._extract_behavioral_features(code1)
            features2 = self._extract_behavioral_features(code2)
            
            # Calculate behavioral distance
            distance = self._calculate_behavioral_distance(features1, features2)
            
            return distance
            
        except Exception as e:
            self.logger.warning(f"Error in behavioral analysis: {e}")
            return 0.5  # Default moderate diversity
    
    def _extract_behavioral_features(self, code: str) -> Dict[str, float]:
        """Extract features that indicate behavioral characteristics."""
        # Get comprehensive features from the feature extractor
        all_features = self.feature_extractor.extract_features(code)
        
        # Focus on features that indicate behavioral differences
        behavioral_features = {
            'complexity': all_features.get('cyclomatic_complexity', 1),
            'nesting': all_features.get('nesting_complexity', 1.0),
            'control_flow_diversity': all_features.get('control_flow_diversity', 0.0),
            'function_density': all_features.get('function_count', 0) / max(all_features.get('line_count', 1), 1),
            'comprehension_usage': all_features.get('comprehension_usage', 0),
            'import_diversity': all_features.get('import_diversity', 0)
        }
        
        # Add execution pattern analysis
        behavioral_features.update(self._analyze_execution_patterns(code))
        
        return behavioral_features
    
    def _analyze_execution_patterns(self, code: str) -> Dict[str, float]:
        """Analyze patterns that affect execution behavior."""
        try:
            tree = ast.parse(code)
            patterns = {}
            
            # Analyze algorithmic patterns
            patterns.update(self._analyze_algorithmic_patterns(tree))
            
            # Analyze data structure usage
            patterns.update(self._analyze_data_structure_patterns(tree))
            
            # Analyze computational complexity indicators
            patterns.update(self._analyze_complexity_indicators(tree))
            
            return patterns
            
        except SyntaxError:
            return {}
    
    def _analyze_algorithmic_patterns(self, tree: ast.AST) -> Dict[str, float]:
        """Analyze algorithmic patterns in the code."""
        patterns = {
            'recursive_calls': 0.0,
            'nested_loops': 0.0,
            'conditional_complexity': 0.0,
            'iteration_patterns': 0.0
        }
        
        function_names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_names.add(node.name)
        
        loop_depth = 0
        max_loop_depth = 0
        conditional_depth = 0
        
        for node in ast.walk(tree):
            # Detect recursive calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in function_names:
                    patterns['recursive_calls'] += 1.0
            
            # Track loop nesting
            elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
                loop_depth += 1
                max_loop_depth = max(max_loop_depth, loop_depth)
                patterns['iteration_patterns'] += 1.0
            
            # Track conditional complexity
            elif isinstance(node, ast.If):
                conditional_depth += 1
                patterns['conditional_complexity'] += 1.0
                # Add complexity for chained conditions
                if isinstance(node.test, ast.BoolOp):
                    patterns['conditional_complexity'] += len(node.test.values) - 1
        
        patterns['nested_loops'] = float(max_loop_depth)
        
        return patterns
    
    def _analyze_data_structure_patterns(self, tree: ast.AST) -> Dict[str, float]:
        """Analyze data structure usage patterns."""
        patterns = {
            'list_operations': 0.0,
            'dict_operations': 0.0,
            'set_operations': 0.0,
            'string_operations': 0.0,
            'collection_complexity': 0.0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr
                    
                    # List operations
                    if method_name in ['append', 'extend', 'insert', 'remove', 'pop', 'sort', 'reverse']:
                        patterns['list_operations'] += 1.0
                    
                    # Dictionary operations
                    elif method_name in ['get', 'keys', 'values', 'items', 'update', 'pop', 'setdefault']:
                        patterns['dict_operations'] += 1.0
                    
                    # Set operations
                    elif method_name in ['add', 'remove', 'discard', 'union', 'intersection', 'difference']:
                        patterns['set_operations'] += 1.0
                    
                    # String operations
                    elif method_name in ['split', 'join', 'replace', 'strip', 'lower', 'upper', 'format']:
                        patterns['string_operations'] += 1.0
            
            # Collection literals
            elif isinstance(node, (ast.List, ast.Tuple)):
                patterns['collection_complexity'] += len(node.elts)
            elif isinstance(node, ast.Dict):
                patterns['collection_complexity'] += len(node.keys)
            elif isinstance(node, ast.Set):
                patterns['collection_complexity'] += len(node.elts)
        
        return patterns
    
    def _analyze_complexity_indicators(self, tree: ast.AST) -> Dict[str, float]:
        """Analyze indicators of computational complexity."""
        indicators = {
            'memory_complexity': 0.0,
            'time_complexity_indicators': 0.0,
            'io_operations': 0.0,
            'external_calls': 0.0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                    
                    # I/O operations
                    if func_name in ['open', 'print', 'input', 'read', 'write']:
                        indicators['io_operations'] += 1.0
                    
                    # Built-in functions that might indicate complexity
                    elif func_name in ['sorted', 'map', 'filter', 'reduce', 'enumerate', 'zip']:
                        indicators['time_complexity_indicators'] += 1.0
                    
                    # Memory-intensive operations
                    elif func_name in ['list', 'dict', 'set', 'tuple']:
                        indicators['memory_complexity'] += 1.0
                
                elif isinstance(node.func, ast.Attribute):
                    # External library calls (approximation)
                    if isinstance(node.func.value, ast.Name):
                        indicators['external_calls'] += 1.0
        
        return indicators
    
    def _calculate_behavioral_distance(self, features1: Dict[str, float], features2: Dict[str, float]) -> float:
        """Calculate distance between behavioral feature vectors."""
        all_features = set(features1.keys()) | set(features2.keys())
        
        if not all_features:
            return 0.0
        
        # Calculate normalized distances for each feature
        distances = []
        
        for feature in all_features:
            val1 = features1.get(feature, 0.0)
            val2 = features2.get(feature, 0.0)
            
            # Normalize by the maximum value seen
            max_val = max(val1, val2, 1.0)  # Avoid division by zero
            normalized_distance = abs(val1 - val2) / max_val
            
            distances.append(normalized_distance)
        
        # Return average distance
        return sum(distances) / len(distances) if distances else 0.0
    
    def get_name(self) -> str:
        return "behavioral_diversity"


class StructuralDiversityMetric(DiversityMetric):
    """
    Measures structural diversity based on code organization and patterns.
    
    This metric focuses on high-level structural differences like function
    organization, class hierarchies, and overall code architecture.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".StructuralDiversityMetric")
    
    def calculate_diversity(self, code1: str, code2: str) -> float:
        """Calculate structural diversity based on code organization."""
        try:
            structure1 = self._extract_structural_features(code1)
            structure2 = self._extract_structural_features(code2)
            
            diversity = self._calculate_structural_distance(structure1, structure2)
            return diversity
            
        except Exception as e:
            self.logger.warning(f"Error in structural analysis: {e}")
            return 0.5  # Default moderate diversity
    
    def _extract_structural_features(self, code: str) -> Dict[str, Any]:
        """Extract structural features from code."""
        try:
            tree = ast.parse(code)
            features = {}
            
            # Extract organizational features
            features.update(self._analyze_code_organization(tree))
            
            # Extract modular structure
            features.update(self._analyze_modular_structure(tree))
            
            # Extract design patterns
            features.update(self._analyze_design_patterns(tree))
            
            return features
            
        except SyntaxError:
            return {}
    
    def _analyze_code_organization(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze how code is organized structurally."""
        organization = {
            'top_level_functions': 0,
            'top_level_classes': 0,
            'nested_functions': 0,
            'nested_classes': 0,
            'global_variables': 0,
            'import_statements': 0,
            'code_blocks': []
        }
        
        # Analyze top-level vs nested definitions
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Check if it's top-level or nested
                parent_classes = [p for p in ast.walk(tree) 
                                if isinstance(p, ast.ClassDef) and node in ast.walk(p)]
                parent_functions = [p for p in ast.walk(tree) 
                                  if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)) 
                                  and p != node and node in ast.walk(p)]
                
                if not parent_classes and not parent_functions:
                    organization['top_level_functions'] += 1
                else:
                    organization['nested_functions'] += 1
            
            elif isinstance(node, ast.ClassDef):
                # Check if it's top-level or nested
                parent_classes = [p for p in ast.walk(tree) 
                                if isinstance(p, ast.ClassDef) and p != node and node in ast.walk(p)]
                
                if not parent_classes:
                    organization['top_level_classes'] += 1
                else:
                    organization['nested_classes'] += 1
            
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                organization['import_statements'] += 1
            
            elif isinstance(node, ast.Assign):
                # Count global variable assignments (simplified)
                if isinstance(node.targets[0], ast.Name):
                    organization['global_variables'] += 1
        
        # Analyze code block structure
        organization['code_blocks'] = self._extract_code_blocks(tree)
        
        return organization
    
    def _analyze_modular_structure(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze modular structure and dependencies."""
        structure = {
            'function_call_graph': {},
            'class_hierarchy': {},
            'module_dependencies': set(),
            'coupling_metrics': {}
        }
        
        # Build function call graph
        function_names = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_names.add(node.name)
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls = []
                for child in ast.walk(node):
                    if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                        if child.func.id in function_names:
                            calls.append(child.func.id)
                structure['function_call_graph'][node.name] = calls
        
        # Analyze class hierarchy
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                structure['class_hierarchy'][node.name] = bases
        
        # Extract module dependencies
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    structure['module_dependencies'].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    structure['module_dependencies'].add(node.module)
        
        # Calculate coupling metrics
        structure['coupling_metrics'] = {
            'function_coupling': len(structure['function_call_graph']),
            'class_coupling': sum(len(bases) for bases in structure['class_hierarchy'].values()),
            'external_dependencies': len(structure['module_dependencies'])
        }
        
        return structure
    
    def _analyze_design_patterns(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze usage of common design patterns."""
        patterns = {
            'iterator_pattern': 0,
            'context_manager_pattern': 0,
            'decorator_pattern': 0,
            'property_pattern': 0,
            'singleton_indicators': 0,
            'factory_indicators': 0
        }
        
        for node in ast.walk(tree):
            # Iterator pattern indicators
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in ['__iter__', '__next__']:
                    patterns['iterator_pattern'] += 1
                elif node.name in ['__enter__', '__exit__']:
                    patterns['context_manager_pattern'] += 1
                elif node.decorator_list:
                    patterns['decorator_pattern'] += len(node.decorator_list)
            
            # Property pattern
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'property':
                    patterns['property_pattern'] += 1
            
            # Decorator usage
            elif isinstance(node, ast.Name):
                if node.id in ['@property', '@staticmethod', '@classmethod']:
                    patterns['decorator_pattern'] += 1
        
        return patterns
    
    def _extract_code_blocks(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract information about code blocks and their structure."""
        blocks = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                block_info = {
                    'type': type(node).__name__,
                    'name': node.name,
                    'size': len(node.body),
                    'complexity': self._estimate_block_complexity(node)
                }
                blocks.append(block_info)
        
        return blocks
    
    def _estimate_block_complexity(self, node: ast.AST) -> int:
        """Estimate the complexity of a code block."""
        complexity = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, ast.Try)):
                complexity += 1
        return complexity
    
    def _calculate_structural_distance(self, struct1: Dict[str, Any], struct2: Dict[str, Any]) -> float:
        """Calculate distance between structural features."""
        distances = []
        
        # Organization distance
        org_features = ['top_level_functions', 'top_level_classes', 'nested_functions', 
                       'nested_classes', 'global_variables', 'import_statements']
        
        for feature in org_features:
            val1 = struct1.get(feature, 0)
            val2 = struct2.get(feature, 0)
            max_val = max(val1, val2, 1)
            distances.append(abs(val1 - val2) / max_val)
        
        # Coupling metrics distance
        coupling1 = struct1.get('coupling_metrics', {})
        coupling2 = struct2.get('coupling_metrics', {})
        
        for metric in ['function_coupling', 'class_coupling', 'external_dependencies']:
            val1 = coupling1.get(metric, 0)
            val2 = coupling2.get(metric, 0)
            max_val = max(val1, val2, 1)
            distances.append(abs(val1 - val2) / max_val)
        
        # Design patterns distance
        patterns1 = struct1.get('design_patterns', {}) if 'design_patterns' in struct1 else struct1
        patterns2 = struct2.get('design_patterns', {}) if 'design_patterns' in struct2 else struct2
        
        pattern_features = ['iterator_pattern', 'context_manager_pattern', 'decorator_pattern',
                           'property_pattern', 'singleton_indicators', 'factory_indicators']
        
        for feature in pattern_features:
            val1 = patterns1.get(feature, 0)
            val2 = patterns2.get(feature, 0)
            max_val = max(val1, val2, 1)
            distances.append(abs(val1 - val2) / max_val)
        
        return sum(distances) / len(distances) if distances else 0.0
    
    def get_name(self) -> str:
        return "structural_diversity"


class TextualDiversityMetric(DiversityMetric):
    """
    Enhanced textual diversity metric that goes beyond simple edit distance.
    
    This metric considers token-level differences, identifier patterns,
    and lexical diversity while being more sophisticated than basic string comparison.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".TextualDiversityMetric")
    
    def calculate_diversity(self, code1: str, code2: str) -> float:
        """Calculate enhanced textual diversity."""
        try:
            # Multiple textual diversity measures
            measures = []
            
            # Token-level diversity
            token_div = self._calculate_token_diversity(code1, code2)
            measures.append(('token', token_div, 0.4))
            
            # Identifier diversity
            identifier_div = self._calculate_identifier_diversity(code1, code2)
            measures.append(('identifier', identifier_div, 0.3))
            
            # Lexical diversity
            lexical_div = self._calculate_lexical_diversity(code1, code2)
            measures.append(('lexical', lexical_div, 0.2))
            
            # Basic string similarity (as baseline)
            string_div = 1.0 - difflib.SequenceMatcher(None, code1, code2).ratio()
            measures.append(('string', string_div, 0.1))
            
            # Calculate weighted average
            total_weight = sum(weight for _, _, weight in measures)
            weighted_sum = sum(div * weight for _, div, weight in measures)
            
            return weighted_sum / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            self.logger.warning(f"Error in textual analysis: {e}")
            return 1.0 - difflib.SequenceMatcher(None, code1, code2).ratio()
    
    def _calculate_token_diversity(self, code1: str, code2: str) -> float:
        """Calculate diversity at the token level."""
        try:
            tokens1 = self._tokenize_code(code1)
            tokens2 = self._tokenize_code(code2)
            
            # Calculate Jaccard distance on token sets
            set1, set2 = set(tokens1), set(tokens2)
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            
            jaccard_similarity = intersection / union if union > 0 else 0.0
            
            # Also consider token order with sequence matching
            sequence_similarity = difflib.SequenceMatcher(None, tokens1, tokens2).ratio()
            
            # Combine both measures
            token_similarity = (jaccard_similarity + sequence_similarity) / 2
            return 1.0 - token_similarity
            
        except Exception:
            return 1.0 - difflib.SequenceMatcher(None, code1, code2).ratio()
    
    def _tokenize_code(self, code: str) -> List[str]:
        """Tokenize code into meaningful units."""
        import re
        
        # Simple tokenization: split on whitespace and common delimiters
        token_pattern = r'\w+|[(){}[\],.:;=+\-*/&|<>!]'
        tokens = re.findall(token_pattern, code)
        
        # Filter out very short tokens and common noise
        meaningful_tokens = [token for token in tokens 
                           if len(token) > 1 or token in '(){}[]']
        
        return meaningful_tokens
    
    def _calculate_identifier_diversity(self, code1: str, code2: str) -> float:
        """Calculate diversity based on identifier usage."""
        try:
            identifiers1 = self._extract_identifiers(code1)
            identifiers2 = self._extract_identifiers(code2)
            
            if not identifiers1 and not identifiers2:
                return 0.0
            
            # Calculate diversity in identifier sets
            set1, set2 = set(identifiers1), set(identifiers2)
            intersection = len(set1 & set2)
            union = len(set1 | set2)
            
            jaccard_diversity = 1.0 - (intersection / union if union > 0 else 0.0)
            
            # Also consider identifier naming patterns
            pattern_diversity = self._calculate_naming_pattern_diversity(identifiers1, identifiers2)
            
            return (jaccard_diversity + pattern_diversity) / 2
            
        except Exception:
            return 0.5  # Default moderate diversity
    
    def _extract_identifiers(self, code: str) -> List[str]:
        """Extract identifiers from code."""
        try:
            tree = ast.parse(code)
            identifiers = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    identifiers.append(node.id)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    identifiers.append(node.name)
                elif isinstance(node, ast.arg):
                    identifiers.append(node.arg)
            
            # Filter out Python keywords and built-ins
            python_keywords = {'def', 'class', 'if', 'else', 'for', 'while', 'try', 'except',
                             'True', 'False', 'None', 'and', 'or', 'not', 'in', 'is'}
            
            return [ident for ident in identifiers if ident not in python_keywords]
            
        except SyntaxError:
            # Fallback to regex-based extraction
            import re
            identifier_pattern = r'\b[a-zA-Z_][a-zA-Z0-9_]*\b'
            return re.findall(identifier_pattern, code)
    
    def _calculate_naming_pattern_diversity(self, identifiers1: List[str], identifiers2: List[str]) -> float:
        """Calculate diversity in naming patterns."""
        import re
        
        def classify_naming_style(identifier):
            if re.match(r'^[a-z_][a-z0-9_]*$', identifier):
                return 'snake_case'
            elif re.match(r'^[a-z][a-zA-Z0-9]*$', identifier):
                return 'camelCase'
            elif re.match(r'^[A-Z][a-zA-Z0-9]*$', identifier):
                return 'PascalCase'
            elif re.match(r'^[A-Z_][A-Z0-9_]*$', identifier):
                return 'UPPER_CASE'
            else:
                return 'mixed'
        
        # Classify naming styles in both identifier sets
        styles1 = [classify_naming_style(ident) for ident in identifiers1]
        styles2 = [classify_naming_style(ident) for ident in identifiers2]
        
        # Calculate style distribution differences
        counter1 = Counter(styles1)
        counter2 = Counter(styles2)
        
        all_styles = set(counter1.keys()) | set(counter2.keys())
        
        if not all_styles:
            return 0.0
        
        # Calculate difference in style distributions
        total_diff = 0.0
        total_count = sum(counter1.values()) + sum(counter2.values())
        
        for style in all_styles:
            count1 = counter1.get(style, 0)
            count2 = counter2.get(style, 0)
            
            if total_count > 0:
                freq1 = count1 / sum(counter1.values()) if counter1 else 0
                freq2 = count2 / sum(counter2.values()) if counter2 else 0
                total_diff += abs(freq1 - freq2)
        
        return total_diff / 2  # Normalize to [0, 1]
    
    def _calculate_lexical_diversity(self, code1: str, code2: str) -> float:
        """Calculate lexical diversity using vocabulary richness measures."""
        def calculate_ttr(text):
            """Calculate Type-Token Ratio (TTR)."""
            tokens = self._tokenize_code(text)
            if not tokens:
                return 0.0
            unique_tokens = set(tokens)
            return len(unique_tokens) / len(tokens)
        
        def calculate_mtld(text):
            """Calculate Measure of Textual Lexical Diversity (simplified)."""
            tokens = self._tokenize_code(text)
            if len(tokens) < 10:
                return 0.0
            
            # Simple MTLD approximation
            unique_tokens = set()
            segments = 0
            current_ttr = 0.0
            
            for i, token in enumerate(tokens):
                unique_tokens.add(token)
                current_ttr = len(unique_tokens) / (i + 1)
                
                if current_ttr < 0.72:  # TTR threshold
                    segments += 1
                    unique_tokens.clear()
            
            return len(tokens) / max(segments, 1)
        
        # Calculate lexical diversity measures for both codes
        ttr1, ttr2 = calculate_ttr(code1), calculate_ttr(code2)
        mtld1, mtld2 = calculate_mtld(code1), calculate_mtld(code2)
        
        # Calculate differences in lexical richness
        ttr_diff = abs(ttr1 - ttr2)
        mtld_diff = abs(mtld1 - mtld2) / max(mtld1, mtld2, 1.0)
        
        return (ttr_diff + mtld_diff) / 2
    
    def get_name(self) -> str:
        return "textual_diversity"


class CompositeDiversityMetric:
    """
    Composite diversity metric that combines multiple diversity measures
    to provide a comprehensive diversity score.
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize composite diversity metric.
        
        Args:
            weights: Dictionary mapping metric names to weights.
                    Default weights will be used if not provided.
        """
        self.metrics = {
            'semantic': SemanticSimilarityMetric(),
            'behavioral': BehavioralDiversityMetric(),
            'structural': StructuralDiversityMetric(),
            'textual': TextualDiversityMetric()
        }
        
        # Default weights emphasizing semantic and behavioral diversity
        self.weights = weights or {
            'semantic': 0.35,
            'behavioral': 0.35,
            'structural': 0.20,
            'textual': 0.10
        }
        
        # Normalize weights
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in self.weights.items()}
        
        self.logger = logging.getLogger(__name__ + ".CompositeDiversityMetric")
    
    def calculate_diversity(self, code1: str, code2: str) -> DiversityScore:
        """
        Calculate comprehensive diversity score between two code samples.
        
        Args:
            code1: First code sample
            code2: Second code sample
            
        Returns:
            DiversityScore object with detailed breakdown
        """
        scores = {}
        metadata = {}
        
        for name, metric in self.metrics.items():
            try:
                score = metric.calculate_diversity(code1, code2)
                scores[name] = score
                metadata[f"{name}_metric"] = metric.get_name()
            except Exception as e:
                self.logger.warning(f"Error calculating {name} diversity: {e}")
                scores[name] = 0.5  # Default moderate diversity
        
        # Calculate weighted total
        total_score = sum(scores[name] * self.weights.get(name, 0) 
                         for name in scores.keys())
        
        return DiversityScore(
            total_score=total_score,
            semantic_score=scores.get('semantic', 0.0),
            behavioral_score=scores.get('behavioral', 0.0),
            structural_score=scores.get('structural', 0.0),
            textual_score=scores.get('textual', 0.0),
            metadata=metadata
        )
    
    def get_metric_weights(self) -> Dict[str, float]:
        """Get current metric weights."""
        return self.weights.copy()
    
    def set_metric_weights(self, weights: Dict[str, float]) -> None:
        """Set new metric weights."""
        # Normalize weights
        total_weight = sum(weights.values())
        if total_weight > 0:
            self.weights = {k: v / total_weight for k, v in weights.items()}
        else:
            self.logger.warning("Invalid weights provided, keeping existing weights")


# Global composite diversity metric instance
_diversity_metric: Optional[CompositeDiversityMetric] = None


def get_diversity_metric() -> CompositeDiversityMetric:
    """Get the global composite diversity metric instance."""
    global _diversity_metric
    if _diversity_metric is None:
        _diversity_metric = CompositeDiversityMetric()
    return _diversity_metric


def calculate_program_diversity(code1: str, code2: str) -> DiversityScore:
    """
    Convenience function to calculate diversity between two code samples.
    
    Args:
        code1: First code sample
        code2: Second code sample
        
    Returns:
        DiversityScore object with comprehensive diversity metrics
    """
    metric = get_diversity_metric()
    return metric.calculate_diversity(code1, code2)