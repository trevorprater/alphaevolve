"""
This module defines the PromptSampler class which is responsible 
for constructing prompts for large language models (LLMs).
"""

from typing import List, Optional

from alpha_evolve.program_database import ProgramDatabase, ProgramEntry


class PromptSampler:
    """
    A class responsible for constructing prompts for LLMs by sampling
    and formatting program entries from the program database.
    """
    
    def __init__(self, program_database: ProgramDatabase):
        """
        Initialize a new PromptSampler.
        
        Args:
            program_database: A ProgramDatabase instance to sample programs from.
        """
        self.program_database = program_database
    
    def _format_program_for_prompt(self, program_entry: ProgramEntry, role: str) -> str:
        """
        Format a program entry for inclusion in a prompt.
        
        Args:
            program_entry: The ProgramEntry to format.
            role: The role of this program in the prompt (e.g., 'Parent Program' or 'Inspiration Program').
            
        Returns:
            A formatted string with the program's details.
        """
        # Format the scores section
        scores_text = "\n".join([f"  - {key}: {value}" for key, value in program_entry.scores.items()])
        
        # Build the complete formatted text
        formatted_text = f"""
### {role} (ID: {program_entry.id})

#### Scores:
{scores_text}

#### Code:
```python
{program_entry.code}
```
"""
        return formatted_text
    
    def create_evolution_prompt(
        self, 
        parent_program_ids: List[str], 
        inspiration_program_ids: List[str], 
        task_context: Optional[str] = None, 
        desired_output_format: str = 'diff'
    ) -> str:
        """
        Create a prompt for an LLM to evolve code based on parent and inspiration programs.
        
        Args:
            parent_program_ids: List of IDs for parent programs to evolve.
            inspiration_program_ids: List of IDs for programs to use as inspiration.
            task_context: Optional context about the task to include in the prompt.
            desired_output_format: The desired format for the LLM's output, defaults to 'diff'.
                                  Supports 'diff' or 'full_code'.
        
        Returns:
            A complete prompt string for the LLM.
            
        Raises:
            ValueError: If any of the specified program IDs are not found in the database.
        """
        # Retrieve parent programs
        parent_programs = []
        for program_id in parent_program_ids:
            program = self.program_database.get_program_by_id(program_id)
            if program is None:
                raise ValueError(f"Parent program with ID {program_id} not found in the database")
            parent_programs.append(program)
        
        # Retrieve inspiration programs
        inspiration_programs = []
        for program_id in inspiration_program_ids:
            program = self.program_database.get_program_by_id(program_id)
            if program is None:
                raise ValueError(f"Inspiration program with ID {program_id} not found in the database")
            inspiration_programs.append(program)
        
        # Create system instruction based on the desired output format
        if desired_output_format == 'diff':
            output_instructions = """
Provide your changes in a diff format like this:

<<<<<<<< SEARCH
[original code to replace]
========
[new code to insert]
>>>>>>>> REPLACE

You can include multiple diff blocks if needed.
"""
        else:  # full_code
            output_instructions = """
Provide the complete evolved code block.
"""
        
        # Construct the system instruction
        system_instruction = f"""
You are an expert coding assistant. Your task is to modify the given Python code of the 'parent program(s)' to improve its performance on the defined metrics. Use the 'inspiration program(s)' for ideas.

{output_instructions}
"""
        
        # Format parent programs
        parent_programs_text = "\n".join([
            self._format_program_for_prompt(program, f"Parent Program {i+1}")
            for i, program in enumerate(parent_programs)
        ])
        
        # Format inspiration programs
        inspiration_programs_text = "\n".join([
            self._format_program_for_prompt(program, f"Inspiration Program {i+1}")
            for i, program in enumerate(inspiration_programs)
        ])
        
        # Include task context if provided
        task_context_text = ""
        if task_context:
            task_context_text = f"""
### Task Context
{task_context}
"""
        
        # Assemble the full prompt
        prompt = f"""
{system_instruction}

{task_context_text}

## Parent Programs to Evolve
{parent_programs_text}

## Inspiration Programs
{inspiration_programs_text}

## Your Task
Evolve the parent program(s) to improve performance on the metrics shown above. 
The inspiration program(s) may give you ideas for improvements.
"""
        
        return prompt.strip()