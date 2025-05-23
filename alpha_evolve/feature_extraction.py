"""
Advanced feature extraction for MAP-Elites archive in AlphaEvolve.

This module provides sophisticated feature descriptors including AST-based complexity,
cyclomatic complexity, execution patterns, and other metrics for program analysis.
"""

import ast
import re
import math
import hashlib
from typing import Dict, Any, List, Tuple, Set, Optional, Union, Callable
from dataclasses import dataclass
from collections import defaultdict, Counter
import logging


@dataclass
class FeatureDescriptor:
    """
    Represents a feature descriptor with metadata.
    
    Attributes:
        name: Unique name for the feature
        description: Human-readable description
        data_type: Type of the feature value ('float', 'int', 'categorical')
        range_min: Minimum expected value (for numeric features)
        range_max: Maximum expected value (for numeric features)
        categories: Valid categories (for categorical features)
        extract_fn: Function to extract this feature from code
    """
    name: str
    description: str
    data_type: str  # 'float', 'int', 'categorical'
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    categories: Optional[List[str]] = None
    extract_fn: Optional[Callable[[str], Any]] = None


class ASTAnalyzer:
    """
    Analyzes Python code using Abstract Syntax Tree (AST) for sophisticated metrics.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".ASTAnalyzer")
    
    def analyze_code(self, code: str) -> Dict[str, Any]:
        """
        Perform comprehensive AST analysis of Python code.
        
        Args:
            code: Python source code as string
            
        Returns:
            Dictionary containing various AST-based metrics
        """
        try:
            tree = ast.parse(code)
            
            analysis = {
                'ast_depth': self._calculate_ast_depth(tree),
                'cyclomatic_complexity': self._calculate_cyclomatic_complexity(tree),
                'node_counts': self._count_node_types(tree),
                'function_metrics': self._analyze_functions(tree),
                'class_metrics': self._analyze_classes(tree),
                'import_analysis': self._analyze_imports(tree),
                'variable_analysis': self._analyze_variables(tree),
                'control_flow_complexity': self._analyze_control_flow(tree),
                'nesting_levels': self._analyze_nesting_levels(tree),
                'comprehension_usage': self._analyze_comprehensions(tree)
            }
            
            return analysis
            
        except SyntaxError as e:
            self.logger.warning(f"Syntax error in code analysis: {e}")
            return self._get_default_analysis_with_error(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error in AST analysis: {e}")
            return self._get_default_analysis_with_error(str(e))
    
    def _calculate_ast_depth(self, node: ast.AST) -> int:
        """Calculate the maximum depth of the AST tree."""
        if not hasattr(node, '_fields') or not node._fields:
            return 1
        
        max_child_depth = 0
        for field, value in ast.iter_fields(node):
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, ast.AST):
                        max_child_depth = max(max_child_depth, self._calculate_ast_depth(item))
            elif isinstance(value, ast.AST):
                max_child_depth = max(max_child_depth, self._calculate_ast_depth(value))
        
        return 1 + max_child_depth
    
    def _calculate_cyclomatic_complexity(self, tree: ast.AST) -> int:
        """
        Calculate McCabe cyclomatic complexity.
        
        Counts decision points in the code: if, while, for, except, etc.
        """
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(node, ast.ExceptHandler):
                complexity += 1
            elif isinstance(node, ast.comprehension):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                # Each additional condition in boolean operations adds complexity
                complexity += len(node.values) - 1
            elif isinstance(node, ast.Compare):
                # Multiple comparisons (a < b < c) add complexity
                complexity += len(node.comparators)
        
        return complexity
    
    def _count_node_types(self, tree: ast.AST) -> Dict[str, int]:
        """Count occurrences of different AST node types."""
        counts = defaultdict(int)
        
        for node in ast.walk(tree):
            node_type = type(node).__name__
            counts[node_type] += 1
        
        return dict(counts)
    
    def _analyze_functions(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze function definitions in the code."""
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = {
                    'name': node.name,
                    'args_count': len(node.args.args),
                    'decorators_count': len(node.decorator_list),
                    'body_length': len(node.body),
                    'returns_annotation': node.returns is not None,
                    'has_docstring': (len(node.body) > 0 and 
                                    isinstance(node.body[0], ast.Expr) and 
                                    isinstance(node.body[0].value, ast.Constant) and
                                    isinstance(node.body[0].value.value, str)),
                    'is_async': isinstance(node, ast.AsyncFunctionDef)
                }
                functions.append(func_info)
        
        return {
            'function_count': len(functions),
            'avg_args_per_function': sum(f['args_count'] for f in functions) / max(len(functions), 1),
            'avg_body_length': sum(f['body_length'] for f in functions) / max(len(functions), 1),
            'decorated_functions': sum(1 for f in functions if f['decorators_count'] > 0),
            'documented_functions': sum(1 for f in functions if f['has_docstring']),
            'async_functions': sum(1 for f in functions if f['is_async'])
        }
    
    def _analyze_classes(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze class definitions in the code."""
        classes = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_info = {
                    'name': node.name,
                    'base_classes': len(node.bases),
                    'methods_count': sum(1 for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))),
                    'decorators_count': len(node.decorator_list),
                    'body_length': len(node.body)
                }
                classes.append(class_info)
        
        return {
            'class_count': len(classes),
            'avg_methods_per_class': sum(c['methods_count'] for c in classes) / max(len(classes), 1),
            'classes_with_inheritance': sum(1 for c in classes if c['base_classes'] > 0)
        }
    
    def _analyze_imports(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze import statements and dependencies."""
        imports = set()
        from_imports = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    from_imports.add(node.module)
        
        return {
            'direct_imports': len(imports),
            'from_imports': len(from_imports),
            'total_imports': len(imports) + len(from_imports),
            'import_modules': list(imports | from_imports)
        }
    
    def _analyze_variables(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze variable usage patterns."""
        assignments = set()
        names_used = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Store):
                    assignments.add(node.id)
                else:
                    names_used.add(node.id)
        
        return {
            'variables_assigned': len(assignments),
            'unique_names_used': len(names_used),
            'variable_reuse_ratio': len(assignments) / max(len(names_used), 1)
        }
    
    def _analyze_control_flow(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze control flow patterns."""
        control_structures = {
            'if_statements': 0,
            'while_loops': 0,
            'for_loops': 0,
            'try_blocks': 0,
            'with_statements': 0,
            'nested_loops': 0,
            'break_statements': 0,
            'continue_statements': 0,
            'return_statements': 0
        }
        
        loop_depth = 0
        max_loop_depth = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                control_structures['if_statements'] += 1
            elif isinstance(node, ast.While):
                control_structures['while_loops'] += 1
                loop_depth += 1
                max_loop_depth = max(max_loop_depth, loop_depth)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                control_structures['for_loops'] += 1
                loop_depth += 1
                max_loop_depth = max(max_loop_depth, loop_depth)
            elif isinstance(node, ast.Try):
                control_structures['try_blocks'] += 1
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                control_structures['with_statements'] += 1
            elif isinstance(node, ast.Break):
                control_structures['break_statements'] += 1
            elif isinstance(node, ast.Continue):
                control_structures['continue_statements'] += 1
            elif isinstance(node, ast.Return):
                control_structures['return_statements'] += 1
        
        control_structures['max_loop_nesting'] = max_loop_depth
        return control_structures
    
    def _analyze_nesting_levels(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze nesting levels of different constructs."""
        def calculate_nesting(node, depth=0):
            max_depth = depth
            
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor, 
                                    ast.With, ast.AsyncWith, ast.Try, ast.FunctionDef, 
                                    ast.AsyncFunctionDef, ast.ClassDef)):
                    child_depth = calculate_nesting(child, depth + 1)
                    max_depth = max(max_depth, child_depth)
                else:
                    child_depth = calculate_nesting(child, depth)
                    max_depth = max(max_depth, child_depth)
            
            return max_depth
        
        return {
            'max_nesting_depth': calculate_nesting(tree),
            'nesting_complexity_score': calculate_nesting(tree) * self._calculate_cyclomatic_complexity(tree)
        }
    
    def _analyze_comprehensions(self, tree: ast.AST) -> Dict[str, Any]:
        """Analyze usage of comprehensions (list, dict, set, generator)."""
        comprehensions = {
            'list_comprehensions': 0,
            'dict_comprehensions': 0,
            'set_comprehensions': 0,
            'generator_expressions': 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ListComp):
                comprehensions['list_comprehensions'] += 1
            elif isinstance(node, ast.DictComp):
                comprehensions['dict_comprehensions'] += 1
            elif isinstance(node, ast.SetComp):
                comprehensions['set_comprehensions'] += 1
            elif isinstance(node, ast.GeneratorExp):
                comprehensions['generator_expressions'] += 1
        
        comprehensions['total_comprehensions'] = sum(comprehensions.values())
        return comprehensions
    
    def _get_default_analysis_with_error(self, error_msg: str) -> Dict[str, Any]:
        """Return default analysis values when AST parsing fails."""
        return {
            'ast_depth': 0,
            'cyclomatic_complexity': 1,
            'node_counts': {},
            'function_metrics': {'function_count': 0},
            'class_metrics': {'class_count': 0},
            'import_analysis': {'total_imports': 0},
            'variable_analysis': {'variables_assigned': 0},
            'control_flow_complexity': {},
            'nesting_levels': {'max_nesting_depth': 0},
            'comprehension_usage': {'total_comprehensions': 0},
            'analysis_error': error_msg
        }


class TextualAnalyzer:
    """
    Analyzes code using textual patterns and metrics.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__ + ".TextualAnalyzer")
    
    def analyze_code(self, code: str) -> Dict[str, Any]:
        """
        Perform textual analysis of code.
        
        Args:
            code: Python source code as string
            
        Returns:
            Dictionary containing textual metrics
        """
        lines = code.split('\n')
        
        return {
            'line_metrics': self._analyze_lines(lines),
            'character_metrics': self._analyze_characters(code),
            'comment_metrics': self._analyze_comments(lines),
            'string_metrics': self._analyze_strings(code),
            'indentation_metrics': self._analyze_indentation(lines),
            'naming_conventions': self._analyze_naming_conventions(code),
            'code_density': self._analyze_code_density(lines)
        }
    
    def _analyze_lines(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze line-based metrics."""
        non_empty_lines = [line for line in lines if line.strip()]
        
        return {
            'total_lines': len(lines),
            'non_empty_lines': len(non_empty_lines),
            'avg_line_length': sum(len(line) for line in lines) / max(len(lines), 1),
            'max_line_length': max(len(line) for line in lines) if lines else 0,
            'empty_line_ratio': (len(lines) - len(non_empty_lines)) / max(len(lines), 1)
        }
    
    def _analyze_characters(self, code: str) -> Dict[str, Any]:
        """Analyze character-based metrics."""
        return {
            'total_characters': len(code),
            'alphanumeric_ratio': sum(1 for c in code if c.isalnum()) / max(len(code), 1),
            'whitespace_ratio': sum(1 for c in code if c.isspace()) / max(len(code), 1),
            'punctuation_ratio': sum(1 for c in code if c in '()[]{}.,;:') / max(len(code), 1),
            'operator_ratio': sum(1 for c in code if c in '+-*/%=<>!&|^~') / max(len(code), 1)
        }
    
    def _analyze_comments(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze comment patterns."""
        comment_lines = 0
        docstring_lines = 0
        inline_comments = 0
        
        in_multiline_string = False
        multiline_delim = None
        
        for line in lines:
            stripped = line.strip()
            
            # Check for multiline strings (potential docstrings)
            if '"""' in line or "'''" in line:
                if not in_multiline_string:
                    in_multiline_string = True
                    multiline_delim = '"""' if '"""' in line else "'''"
                    docstring_lines += 1
                else:
                    if multiline_delim in line:
                        in_multiline_string = False
                        docstring_lines += 1
                continue
            
            if in_multiline_string:
                docstring_lines += 1
                continue
            
            # Check for single-line comments
            if stripped.startswith('#'):
                comment_lines += 1
            elif '#' in line and not any(q in line[:line.index('#')] for q in ['"', "'"]):
                inline_comments += 1
        
        return {
            'comment_lines': comment_lines,
            'docstring_lines': docstring_lines,
            'inline_comments': inline_comments,
            'comment_ratio': comment_lines / max(len(lines), 1),
            'documentation_ratio': (comment_lines + docstring_lines) / max(len(lines), 1)
        }
    
    def _analyze_strings(self, code: str) -> Dict[str, Any]:
        """Analyze string usage patterns."""
        single_quotes = code.count("'") - code.count("\\'")
        double_quotes = code.count('"') - code.count('\\"')
        triple_quotes = code.count('"""') + code.count("'''")
        
        return {
            'single_quote_strings': single_quotes // 2,  # Approximate
            'double_quote_strings': double_quotes // 2,  # Approximate
            'triple_quote_strings': triple_quotes,
            'string_consistency_score': self._calculate_string_consistency(code)
        }
    
    def _calculate_string_consistency(self, code: str) -> float:
        """Calculate consistency in string quote usage."""
        single_quotes = code.count("'") - code.count("\\'")
        double_quotes = code.count('"') - code.count('\\"')
        
        total_quotes = single_quotes + double_quotes
        if total_quotes == 0:
            return 1.0
        
        # Consistency is higher when one style dominates
        dominant_style = max(single_quotes, double_quotes)
        return dominant_style / total_quotes
    
    def _analyze_indentation(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze indentation patterns."""
        indentations = []
        tab_lines = 0
        space_lines = 0
        mixed_lines = 0
        
        for line in lines:
            if not line.strip():
                continue  # Skip empty lines
            
            leading_spaces = len(line) - len(line.lstrip(' '))
            leading_tabs = len(line) - len(line.lstrip('\t'))
            
            if leading_tabs > 0 and leading_spaces > 0:
                mixed_lines += 1
            elif leading_tabs > 0:
                tab_lines += 1
            elif leading_spaces > 0:
                space_lines += 1
            
            # Calculate total indentation level
            total_indent = leading_spaces + (leading_tabs * 4)  # Assume tabs = 4 spaces
            indentations.append(total_indent)
        
        return {
            'avg_indentation': sum(indentations) / max(len(indentations), 1),
            'max_indentation': max(indentations) if indentations else 0,
            'tab_lines': tab_lines,
            'space_lines': space_lines,
            'mixed_indentation_lines': mixed_lines,
            'indentation_consistency': self._calculate_indentation_consistency(tab_lines, space_lines, mixed_lines)
        }
    
    def _calculate_indentation_consistency(self, tab_lines: int, space_lines: int, mixed_lines: int) -> float:
        """Calculate indentation consistency score."""
        total_indented = tab_lines + space_lines + mixed_lines
        if total_indented == 0:
            return 1.0
        
        # Penalty for mixed indentation
        consistency = 1.0 - (mixed_lines / total_indented)
        
        # Additional penalty if both tabs and spaces are used
        if tab_lines > 0 and space_lines > 0:
            consistency *= 0.5
        
        return max(0.0, consistency)
    
    def _analyze_naming_conventions(self, code: str) -> Dict[str, Any]:
        """Analyze adherence to Python naming conventions."""
        # Simple regex patterns for different naming styles
        snake_case_pattern = re.compile(r'^[a-z_][a-z0-9_]*$')
        camel_case_pattern = re.compile(r'^[a-z][a-zA-Z0-9]*$')
        pascal_case_pattern = re.compile(r'^[A-Z][a-zA-Z0-9]*$')
        upper_snake_pattern = re.compile(r'^[A-Z_][A-Z0-9_]*$')
        
        # Extract identifiers (simplified)
        identifier_pattern = re.compile(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')
        identifiers = identifier_pattern.findall(code)
        
        # Filter out Python keywords and common built-ins
        python_keywords = {'def', 'class', 'if', 'else', 'elif', 'for', 'while', 'try', 'except', 'finally', 
                          'import', 'from', 'as', 'return', 'yield', 'pass', 'break', 'continue', 'lambda',
                          'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None', 'int', 'str', 'list', 'dict'}
        identifiers = [name for name in identifiers if name not in python_keywords]
        
        if not identifiers:
            return {'naming_consistency': 1.0, 'total_identifiers': 0}
        
        naming_styles = {
            'snake_case': sum(1 for name in identifiers if snake_case_pattern.match(name)),
            'camel_case': sum(1 for name in identifiers if camel_case_pattern.match(name)),
            'pascal_case': sum(1 for name in identifiers if pascal_case_pattern.match(name)),
            'upper_snake': sum(1 for name in identifiers if upper_snake_pattern.match(name)),
        }
        
        total_styled = sum(naming_styles.values())
        dominant_style = max(naming_styles.values()) if naming_styles.values() else 0
        
        return {
            'naming_consistency': dominant_style / max(len(identifiers), 1),
            'total_identifiers': len(identifiers),
            'style_distribution': naming_styles,
            'well_named_ratio': total_styled / max(len(identifiers), 1)
        }
    
    def _analyze_code_density(self, lines: List[str]) -> Dict[str, Any]:
        """Analyze code density and structure."""
        code_lines = [line for line in lines if line.strip() and not line.strip().startswith('#')]
        
        # Count statements (simplified)
        statements = 0
        for line in code_lines:
            # Count semicolons (multiple statements per line) and basic statement patterns
            statements += line.count(';') + 1
        
        return {
            'code_lines': len(code_lines),
            'statements_per_line': statements / max(len(code_lines), 1),
            'code_density_ratio': len(code_lines) / max(len(lines), 1),
            'avg_statement_length': sum(len(line.strip()) for line in code_lines) / max(statements, 1)
        }


class AdvancedFeatureExtractor:
    """
    Main feature extraction class that combines AST and textual analysis
    to provide comprehensive code feature descriptors.
    """
    
    def __init__(self):
        self.ast_analyzer = ASTAnalyzer()
        self.textual_analyzer = TextualAnalyzer()
        self.logger = logging.getLogger(__name__ + ".AdvancedFeatureExtractor")
        
        # Define comprehensive feature descriptors
        self.feature_descriptors = self._initialize_feature_descriptors()
    
    def _initialize_feature_descriptors(self) -> Dict[str, FeatureDescriptor]:
        """Initialize the complete set of feature descriptors."""
        descriptors = {}
        
        # Complexity Features
        descriptors['cyclomatic_complexity'] = FeatureDescriptor(
            name='cyclomatic_complexity',
            description='McCabe cyclomatic complexity measure',
            data_type='int',
            range_min=1, range_max=50
        )
        
        descriptors['ast_depth'] = FeatureDescriptor(
            name='ast_depth',
            description='Maximum depth of the Abstract Syntax Tree',
            data_type='int',
            range_min=1, range_max=30
        )
        
        descriptors['nesting_complexity'] = FeatureDescriptor(
            name='nesting_complexity',
            description='Combined nesting depth and cyclomatic complexity',
            data_type='float',
            range_min=1.0, range_max=200.0
        )
        
        # Size and Structure Features
        descriptors['line_count'] = FeatureDescriptor(
            name='line_count',
            description='Total number of lines in the code',
            data_type='int',
            range_min=1, range_max=1000
        )
        
        descriptors['function_count'] = FeatureDescriptor(
            name='function_count',
            description='Number of function definitions',
            data_type='int',
            range_min=0, range_max=50
        )
        
        descriptors['class_count'] = FeatureDescriptor(
            name='class_count',
            description='Number of class definitions',
            data_type='int',
            range_min=0, range_max=20
        )
        
        # Code Quality Features
        descriptors['documentation_ratio'] = FeatureDescriptor(
            name='documentation_ratio',
            description='Ratio of comments and docstrings to total lines',
            data_type='float',
            range_min=0.0, range_max=1.0
        )
        
        descriptors['naming_consistency'] = FeatureDescriptor(
            name='naming_consistency',
            description='Consistency in naming conventions',
            data_type='float',
            range_min=0.0, range_max=1.0
        )
        
        descriptors['indentation_consistency'] = FeatureDescriptor(
            name='indentation_consistency',
            description='Consistency in indentation style',
            data_type='float',
            range_min=0.0, range_max=1.0
        )
        
        # Advanced Features
        descriptors['import_diversity'] = FeatureDescriptor(
            name='import_diversity',
            description='Number of unique imported modules',
            data_type='int',
            range_min=0, range_max=30
        )
        
        descriptors['comprehension_usage'] = FeatureDescriptor(
            name='comprehension_usage',
            description='Usage of Python comprehensions (list, dict, set, generator)',
            data_type='int',
            range_min=0, range_max=20
        )
        
        descriptors['control_flow_diversity'] = FeatureDescriptor(
            name='control_flow_diversity',
            description='Variety in control flow constructs used',
            data_type='float',
            range_min=0.0, range_max=10.0
        )
        
        return descriptors
    
    def extract_features(self, code: str, feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Extract comprehensive features from code.
        
        Args:
            code: Python source code as string
            feature_names: Optional list of specific features to extract.
                          If None, extracts all available features.
        
        Returns:
            Dictionary mapping feature names to their values
        """
        try:
            # Perform both AST and textual analysis
            ast_analysis = self.ast_analyzer.analyze_code(code)
            textual_analysis = self.textual_analyzer.analyze_code(code)
            
            # Extract consolidated features
            features = self._consolidate_features(ast_analysis, textual_analysis)
            
            # Filter features if specific ones are requested
            if feature_names:
                features = {name: features.get(name, 0) for name in feature_names}
            
            return features
            
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {e}")
            # Return default features in case of error
            return self._get_default_features(feature_names or list(self.feature_descriptors.keys()))
    
    def _consolidate_features(self, ast_analysis: Dict[str, Any], textual_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Consolidate AST and textual analysis into final feature values."""
        features = {}
        
        # Direct mappings from AST analysis
        features['cyclomatic_complexity'] = ast_analysis.get('cyclomatic_complexity', 1)
        features['ast_depth'] = ast_analysis.get('ast_depth', 1)
        features['function_count'] = ast_analysis.get('function_metrics', {}).get('function_count', 0)
        features['class_count'] = ast_analysis.get('class_metrics', {}).get('class_count', 0)
        
        # Direct mappings from textual analysis
        features['line_count'] = textual_analysis.get('line_metrics', {}).get('total_lines', 1)
        features['documentation_ratio'] = textual_analysis.get('comment_metrics', {}).get('documentation_ratio', 0.0)
        features['naming_consistency'] = textual_analysis.get('naming_conventions', {}).get('naming_consistency', 1.0)
        features['indentation_consistency'] = textual_analysis.get('indentation_metrics', {}).get('indentation_consistency', 1.0)
        
        # Computed composite features
        features['nesting_complexity'] = ast_analysis.get('nesting_levels', {}).get('nesting_complexity_score', 1.0)
        features['import_diversity'] = ast_analysis.get('import_analysis', {}).get('total_imports', 0)
        features['comprehension_usage'] = ast_analysis.get('comprehension_usage', {}).get('total_comprehensions', 0)
        
        # Control flow diversity (count different types of control structures used)
        control_flow = ast_analysis.get('control_flow_complexity', {})
        control_types_used = sum(1 for count in control_flow.values() if isinstance(count, int) and count > 0)
        features['control_flow_diversity'] = float(control_types_used)
        
        return features
    
    def _get_default_features(self, feature_names: List[str]) -> Dict[str, Any]:
        """Return default feature values when extraction fails."""
        defaults = {
            'cyclomatic_complexity': 1,
            'ast_depth': 1,
            'nesting_complexity': 1.0,
            'line_count': 1,
            'function_count': 0,
            'class_count': 0,
            'documentation_ratio': 0.0,
            'naming_consistency': 1.0,
            'indentation_consistency': 1.0,
            'import_diversity': 0,
            'comprehension_usage': 0,
            'control_flow_diversity': 0.0
        }
        
        return {name: defaults.get(name, 0) for name in feature_names}
    
    def get_feature_descriptor(self, feature_name: str) -> Optional[FeatureDescriptor]:
        """Get the descriptor for a specific feature."""
        return self.feature_descriptors.get(feature_name)
    
    def get_all_feature_descriptors(self) -> Dict[str, FeatureDescriptor]:
        """Get all available feature descriptors."""
        return self.feature_descriptors.copy()
    
    def validate_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and normalize feature values according to their descriptors.
        
        Args:
            features: Dictionary of feature values to validate
            
        Returns:
            Dictionary of validated and normalized feature values
        """
        validated = {}
        
        for name, value in features.items():
            descriptor = self.feature_descriptors.get(name)
            if not descriptor:
                # Unknown feature, keep as-is
                validated[name] = value
                continue
            
            try:
                if descriptor.data_type == 'int':
                    validated_value = int(value)
                elif descriptor.data_type == 'float':
                    validated_value = float(value)
                else:
                    validated_value = value
                
                # Apply range constraints for numeric features
                if descriptor.range_min is not None and validated_value < descriptor.range_min:
                    validated_value = descriptor.range_min
                if descriptor.range_max is not None and validated_value > descriptor.range_max:
                    validated_value = descriptor.range_max
                
                validated[name] = validated_value
                
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid value for feature '{name}': {value}")
                # Use default value based on data type
                if descriptor.data_type == 'int':
                    validated[name] = descriptor.range_min or 0
                elif descriptor.data_type == 'float':
                    validated[name] = descriptor.range_min or 0.0
                else:
                    validated[name] = descriptor.categories[0] if descriptor.categories else 'unknown'
        
        return validated
    
    def calculate_feature_distance(self, features1: Dict[str, Any], features2: Dict[str, Any]) -> float:
        """
        Calculate normalized distance between two feature vectors.
        
        Args:
            features1: First feature vector
            features2: Second feature vector
            
        Returns:
            Normalized distance between 0.0 and 1.0
        """
        common_features = set(features1.keys()) & set(features2.keys())
        
        if not common_features:
            return 1.0  # Maximum distance if no common features
        
        total_distance = 0.0
        
        for feature_name in common_features:
            descriptor = self.feature_descriptors.get(feature_name)
            if not descriptor:
                continue
            
            val1, val2 = features1[feature_name], features2[feature_name]
            
            if descriptor.data_type in ['int', 'float']:
                # Normalize by feature range
                range_size = (descriptor.range_max or 1) - (descriptor.range_min or 0)
                if range_size > 0:
                    normalized_distance = abs(val1 - val2) / range_size
                else:
                    normalized_distance = 0.0 if val1 == val2 else 1.0
            else:
                # Categorical features: 0 if same, 1 if different
                normalized_distance = 0.0 if val1 == val2 else 1.0
            
            total_distance += normalized_distance
        
        # Return average distance across all common features
        return total_distance / len(common_features)


# Global feature extractor instance
_feature_extractor: Optional[AdvancedFeatureExtractor] = None


def get_feature_extractor() -> AdvancedFeatureExtractor:
    """Get the global feature extractor instance."""
    global _feature_extractor
    if _feature_extractor is None:
        _feature_extractor = AdvancedFeatureExtractor()
    return _feature_extractor


def extract_code_features(code: str, feature_names: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Convenience function to extract features from code.
    
    Args:
        code: Python source code as string
        feature_names: Optional list of specific features to extract
        
    Returns:
        Dictionary mapping feature names to their values
    """
    extractor = get_feature_extractor()
    return extractor.extract_features(code, feature_names)