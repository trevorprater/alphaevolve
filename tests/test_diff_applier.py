"""
Tests for the DiffApplier module.
"""
import pytest
from alpha_evolve.diff_applier import DiffApplier, DiffApplicationError


class TestDiffApplier:
    """Test cases for the DiffApplier class."""

    def setup_method(self):
        """Set up the test fixture."""
        self.applier = DiffApplier()

    def test_apply_diff_simple(self):
        """Test applying a simple diff."""
        parent_code = "def example():\n    return 1\n"
        diff_string = """<<<<<<<< SEARCH
def example():
    return 1
========
def example():
    return 2
>>>>>>>> REPLACE"""
        expected = "def example():\n    return 2\n"
        
        result = self.applier.apply_diff(parent_code, diff_string)
        assert result == expected

    def test_apply_diff_with_multiple_matches(self):
        """Test applying a diff with multiple matches (should replace only the first)."""
        parent_code = "value = 1\nprint(value)\nvalue = 1\nprint(value)"
        diff_string = """<<<<<<<< SEARCH
value = 1
========
value = 99
>>>>>>>> REPLACE"""
        expected = "value = 99\nprint(value)\nvalue = 1\nprint(value)"
        
        result = self.applier.apply_diff(parent_code, diff_string)
        assert result == expected

    def test_apply_diff_not_found(self):
        """Test applying a diff when the search block is not found."""
        parent_code = "def example():\n    return 3\n"
        diff_string = """<<<<<<<< SEARCH
def missing():
    pass
========
def missing():
    return None
>>>>>>>> REPLACE"""
        
        with pytest.raises(DiffApplicationError):
            self.applier.apply_diff(parent_code, diff_string)

    def test_apply_diff_invalid_format(self):
        """Test applying a diff with invalid format."""
        parent_code = "def example():\n    return 1\n"
        diff_string = """Invalid diff format"""
        
        with pytest.raises(DiffApplicationError):
            self.applier.apply_diff(parent_code, diff_string)

    def test_apply_diff_empty_search(self):
        """Test applying a diff with an empty search block."""
        parent_code = "def example():\n    return 1\n"
        diff_string = """<<<<<<<< SEARCH
========
# Added comment
>>>>>>>> REPLACE"""
        
        with pytest.raises(DiffApplicationError):
            self.applier.apply_diff(parent_code, diff_string)
            
    def test_apply_diff_multiline(self):
        """Test applying a diff with multi-line search and replace blocks."""
        parent_code = """def complex_function():
    # Initialize variables
    x = 1
    y = 2
    z = 3
    
    # Perform calculation
    result = x * y + z
    
    return result
"""
        diff_string = """<<<<<<<< SEARCH
    # Initialize variables
    x = 1
    y = 2
    z = 3
    
    # Perform calculation
    result = x * y + z
========
    # Initialize improved variables
    x = 10
    y = 20
    z = 30
    
    # Perform optimized calculation
    result = (x + y) * z
>>>>>>>> REPLACE"""
        expected = """def complex_function():
    # Initialize improved variables
    x = 10
    y = 20
    z = 30
    
    # Perform optimized calculation
    result = (x + y) * z
    
    return result
"""
        
        result = self.applier.apply_diff(parent_code, diff_string)
        assert result == expected
        
    def test_apply_diff_empty_replace(self):
        """Test applying a diff with an empty replace block."""
        parent_code = """def example():
    # Debug print statement
    print("Debugging value:", x)
    return x * 2
"""
        diff_string = """<<<<<<<< SEARCH
    # Debug print statement
    print("Debugging value:", x)
========

>>>>>>>> REPLACE"""
        expected = """def example():

    return x * 2
"""
        
        result = self.applier.apply_diff(parent_code, diff_string)
        assert result == expected

    def test_apply_full_block_replace(self):
        """Test replacing a full evolvable block."""
        parent_code = """
def main():
    # EVOLVE-BLOCK-START test_block
    x = 1
    y = 2
    return x + y
    # EVOLVE-BLOCK-END test_block
"""
        new_block = "    x = 10\n    y = 20\n    return x * y"
        
        result = self.applier.apply_full_block_replace(parent_code, "test_block", new_block)
        
        # Check the block content was replaced correctly
        assert "    x = 10" in result
        assert "    y = 20" in result
        assert "    return x * y" in result
        
        # Check the markers are still in place
        assert "# EVOLVE-BLOCK-START test_block" in result
        assert "# EVOLVE-BLOCK-END test_block" in result
        
        # Check the structure is preserved
        assert "def main():" in result

    def test_apply_full_block_replace_not_found(self):
        """Test replacing a full evolvable block when the block is not found."""
        parent_code = """
def main():
    # EVOLVE-BLOCK-START test_block
    x = 1
    y = 2
    return x + y
    # EVOLVE-BLOCK-END test_block
"""
        new_block = "    x = 10\n    y = 20\n    return x * y"
        
        with pytest.raises(DiffApplicationError):
            self.applier.apply_full_block_replace(parent_code, "missing_block", new_block)

    def test_apply_full_block_replace_missing_end(self):
        """Test replacing a full evolvable block when the end marker is missing."""
        parent_code = """
def main():
    # EVOLVE-BLOCK-START test_block
    x = 1
    y = 2
    return x + y
"""
        new_block = "    x = 10\n    y = 20\n    return x * y"
        
        with pytest.raises(DiffApplicationError):
            self.applier.apply_full_block_replace(parent_code, "test_block", new_block)

    def test_apply_full_block_replace_with_newline_handling(self):
        """Test replacing a block with proper newline handling."""
        parent_code = """
def main():
    # EVOLVE-BLOCK-START test_block
    x = 1
    # EVOLVE-BLOCK-END test_block
    return x
"""
        new_block = "    y = 2"  # No trailing newline
        
        result = self.applier.apply_full_block_replace(parent_code, "test_block", new_block)
        
        # Check the block content was replaced correctly
        assert "    y = 2" in result
        assert "    x = 1" not in result
        
        # Check the markers are still in place
        assert "# EVOLVE-BLOCK-START test_block" in result
        assert "# EVOLVE-BLOCK-END test_block" in result
        
        # Check the structure is preserved
        assert "def main():" in result
        assert "    return x" in result
        
    def test_apply_full_block_replace_multiple_blocks(self):
        """Test replacing a specific block when multiple evolvable blocks exist."""
        parent_code = """
def main():
    # EVOLVE-BLOCK-START block1
    x = 1
    # EVOLVE-BLOCK-END block1
    
    # EVOLVE-BLOCK-START block2
    y = 2
    # EVOLVE-BLOCK-END block2
    
    return x + y
"""
        new_block = "    y = 20"
        
        result = self.applier.apply_full_block_replace(parent_code, "block2", new_block)
        
        # Check that block2 was replaced with the new content
        assert "    y = 20" in result
        
        # Check block1 was not modified
        assert "    x = 1" in result
        
        # Check the markers are still in place
        assert "# EVOLVE-BLOCK-START block1" in result
        assert "# EVOLVE-BLOCK-END block1" in result
        assert "# EVOLVE-BLOCK-START block2" in result
        assert "# EVOLVE-BLOCK-END block2" in result
        
        # Check the structure is preserved
        assert "def main():" in result
        assert "return x + y" in result
        
    def test_apply_full_block_replace_empty_block(self):
        """Test replacing an empty evolvable block."""
        parent_code = """
def main():
    # EVOLVE-BLOCK-START empty_block
    # EVOLVE-BLOCK-END empty_block
    return None
"""
        new_block = "    x = 42\n    return x"
        
        result = self.applier.apply_full_block_replace(parent_code, "empty_block", new_block)
        
        # Check the block content was added correctly
        assert "    x = 42" in result
        assert "    return x" in result
        
        # Check the markers are still in place
        assert "# EVOLVE-BLOCK-START empty_block" in result
        assert "# EVOLVE-BLOCK-END empty_block" in result
        
        # Check the structure is preserved
        assert "def main():" in result
        assert "    return None" in result
        
    def test_apply_full_block_replace_with_empty_new_block(self):
        """Test replacing content with an empty new_block_code_string."""
        parent_code = """
def main():
    # EVOLVE-BLOCK-START test_block
    x = 1
    y = 2
    return x + y
    # EVOLVE-BLOCK-END test_block
"""
        new_block = ""
        
        result = self.applier.apply_full_block_replace(parent_code, "test_block", new_block)
        
        # Check the original block content was removed
        assert "    x = 1" not in result
        assert "    y = 2" not in result
        assert "    return x + y" not in result
        
        # Check the markers are still in place
        assert "# EVOLVE-BLOCK-START test_block" in result
        assert "# EVOLVE-BLOCK-END test_block" in result
        
        # Check the structure is preserved
        assert "def main():" in result