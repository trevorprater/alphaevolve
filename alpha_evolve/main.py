"""
AlphaEvolve: Main entry point for running the evolution process
"""

import asyncio
import os
from pathlib import Path

from alpha_evolve.controller import DistributedController
from alpha_evolve.diff_applier import DiffApplier
from alpha_evolve.evaluation_engine import EvaluationEngine
from alpha_evolve.llm_interface import LLMInterface
from alpha_evolve.program_database import ProgramDatabase
from alpha_evolve.prompt_sampler import PromptSampler
from alpha_evolve.task_utils import TaskDefinition


async def main():
    """
    Initialize components and run the evolution process.
    """
    # Define basic configuration
    config = {
        "num_generations": 3,
        "batch_size_new_programs": 2,
        "primary_score_key": "objective",
        "num_parents": 1,
        "num_inspirations": 1,
        "llm_type": "pro",  # Using mock for testing
        "output_format": "diff",
        "migration_frequency": 2,
    }

    # Define feature dimensions bins for MAP-Elites
    # The order must match features tuple in controller.py: (code_length, primary_score)
    feature_dimensions_bins = [
        [0, 50, 100, 1000],  # Bins for code_length feature
        [-float("inf"), 0, 0.5, 1.0],  # Bins for primary_score feature
    ]

    # Get paths to sample code and evaluator
    base_dir = Path(os.path.dirname(os.path.dirname(__file__)))
    initial_code_path = base_dir / "initial_code.py"
    evaluator_path = base_dir / "evaluator.py"

    # Create task definition
    task_definition = TaskDefinition(
        problem_name="sample_optimization",
        initial_code_path=str(initial_code_path),
        evaluate_function_module_path=str(evaluator_path),
        evaluate_function_name="evaluate",
    )

    # Initialize components
    program_db = ProgramDatabase(
        feature_dimensions_bins=feature_dimensions_bins,
        primary_score_key=config["primary_score_key"],
    )

    prompt_sampler = PromptSampler(program_database=program_db)

    llm_interface = LLMInterface()  # Using default mock behavior

    diff_applier = DiffApplier()

    evaluation_engine = EvaluationEngine()

    # Create the controller
    controller = DistributedController(
        task_definition=task_definition,
        program_database=program_db,
        prompt_sampler=prompt_sampler,
        llm_interface=llm_interface,
        diff_applier=diff_applier,
        evaluation_engine=evaluation_engine,
        config=config,
    )

    # Run the evolution process
    print("Starting AlphaEvolve...")
    await controller.run_evolution()
    print("Evolution complete.")

    # Print best results
    best_program = program_db.get_best_program()
    if best_program:
        print("\nBest program found:")
        print(f"  Score: {best_program.scores.get(config['primary_score_key'], 'N/A')}")
        print(f"  ID: {best_program.id}")
        print(f"  Code snippet: {best_program.code[:100]}...")


if __name__ == "__main__":
    asyncio.run(main())
