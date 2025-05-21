"""
DiffApplier module for applying code modifications to program code.

This module provides functionality to apply diffs and full block replacements to code.
"""
import re
from typing import Optional, Tuple


class DiffApplicationError(Exception):
    """Exception raised when a diff cannot be applied to the code."""
    pass


class DiffApplier:
    """
    Utility class for applying code modifications to program code.
    
    This class provides methods for applying diffs and replacing evolvable code blocks.
    """
    
    def apply_diff(self, parent_code_string: str, diff_string: str) -> str:
        """
        Apply a diff to the parent code string.
        
        Args:
            parent_code_string: The original code to modify.
            diff_string: A diff string in the format:
                <<<<<<<< SEARCH
                [original code block to be found and replaced]
                ========
                [new code block to replace the original]
                >>>>>>>> REPLACE
        
        Returns:
            The modified code string with the diff applied.
            
        Raises:
            DiffApplicationError: If the diff cannot be parsed or applied.
        """
        # Parse the diff string to extract the search and replace blocks
        search_block, replace_block = self._parse_diff_string(diff_string)
        
        # Find the search block in the parent code string
        if search_block not in parent_code_string:
            raise DiffApplicationError(f"Search block not found in parent code string")
        
        # Replace the first occurrence of the search block with the replace block
        return parent_code_string.replace(search_block, replace_block, 1)
    
    def apply_full_block_replace(self, parent_code_string: str, evolvable_block_id: str, 
                                new_block_code_string: str) -> str:
        """
        Replace the entire content of an evolvable block.
        
        Args:
            parent_code_string: The original code containing the evolvable block.
            evolvable_block_id: The ID of the evolvable block to replace.
            new_block_code_string: The new code to place between the block markers.
            
        Returns:
            The modified code string with the block replaced.
            
        Raises:
            DiffApplicationError: If the block is not found in the parent code string.
        """
        # Find the evolvable block in the parent code string
        start_marker = f"# EVOLVE-BLOCK-START {evolvable_block_id}"
        end_marker = f"# EVOLVE-BLOCK-END {evolvable_block_id}"
        
        # Get the start and end positions of the block
        start_pos = parent_code_string.find(start_marker)
        if start_pos == -1:
            raise DiffApplicationError(f"Evolvable block with ID '{evolvable_block_id}' not found")
        
        # Find the end of the start marker line
        start_marker_end = parent_code_string.find('\n', start_pos)
        if start_marker_end == -1:
            start_marker_end = len(parent_code_string)
            
        # Find the end marker
        end_pos = parent_code_string.find(end_marker, start_marker_end)
        if end_pos == -1:
            raise DiffApplicationError(f"End marker for evolvable block with ID '{evolvable_block_id}' not found")
        
        # Construct the new code
        new_code = (
            parent_code_string[:start_marker_end + 1] +
            new_block_code_string +
            ('\n' if not new_block_code_string.endswith('\n') and not parent_code_string[end_pos-1:end_pos] == '\n' else '') +
            parent_code_string[end_pos:]
        )
        
        return new_code
    
    def _parse_diff_string(self, diff_string: str) -> Tuple[str, str]:
        """
        Parse a diff string to extract the search and replace blocks.
        
        Args:
            diff_string: A diff string in the specified format.
            
        Returns:
            A tuple containing the search block and the replace block.
            
        Raises:
            DiffApplicationError: If the diff string cannot be parsed.
        """
        # Define regex pattern to match the diff format
        pattern = r'<<<<<<<< SEARCH\n(.*?)\n========\n(.*?)\n>>>>>>>> REPLACE'
        match = re.search(pattern, diff_string, re.DOTALL)
        
        if not match:
            raise DiffApplicationError("Invalid diff format. Expected format: "
                                    "<<<<<<<< SEARCH\\n[original code]\\n========\\n[new code]\\n>>>>>>>> REPLACE")
        
        search_block = match.group(1)
        replace_block = match.group(2)
        
        return search_block, replace_block