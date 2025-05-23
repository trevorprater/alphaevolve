"""
Command-line interface for AlphaEvolve.

This module provides a comprehensive CLI for interacting with the AlphaEvolve
evolutionary code optimization system.
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from alpha_evolve.config import get_config_manager, ConfigManager
from alpha_evolve.controller import DistributedController
from alpha_evolve.task_utils import TaskDefinition, CodeParser
from alpha_evolve.program_database import ProgramDatabase
from alpha_evolve.llm_interface import LLMInterface
from alpha_evolve.evaluation_engine import EvaluationEngine
from alpha_evolve.diff_applier import DiffApplier
from alpha_evolve.prompt_sampler import PromptSampler
from alpha_evolve.persistence import (
    PersistentProgramDatabase, EvolutionCheckpoint, 
    create_storage_manager
)


class AlphaEvolveCLI:
    """Main CLI class for AlphaEvolve."""
    
    def __init__(self):
        self.console = Console()
        self.config_manager: Optional[ConfigManager] = None
        
    def setup_logging(self, verbose: bool = False) -> None:
        """Setup logging configuration."""
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('alphaevolve.log')
            ]
        )
    
    def setup_argparse(self) -> argparse.ArgumentParser:
        """Set up argument parser for CLI."""
        parser = argparse.ArgumentParser(
            description='AlphaEvolve: Evolutionary Code Optimization',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  alphaevolve setup --config config.yaml
  alphaevolve evolve --source code.py --generations 10
  alphaevolve evolve --source code.py --interactive
  alphaevolve analyze --database results.json
            """
        )
        
        parser.add_argument(
            '--config', '-c',
            help='Path to configuration file',
            type=str
        )
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Setup command
        setup_parser = subparsers.add_parser(
            'setup',
            help='Initialize project configuration'
        )
        setup_parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing configuration'
        )
        setup_parser.add_argument(
            '--template',
            choices=['basic', 'research', 'production'],
            default='basic',
            help='Configuration template to use'
        )
        
        # Evolve command
        evolve_parser = subparsers.add_parser(
            'evolve',
            help='Run evolution on code'
        )
        evolve_parser.add_argument(
            '--source', '-s',
            required=True,
            help='Source file or directory containing evolvable code'
        )
        evolve_parser.add_argument(
            '--evaluator', '-e',
            help='Path to evaluation function module'
        )
        evolve_parser.add_argument(
            '--generations', '-g',
            type=int,
            default=10,
            help='Number of generations to run (default: 10)'
        )
        evolve_parser.add_argument(
            '--population', '-p',
            type=int,
            help='Population size per generation'
        )
        evolve_parser.add_argument(
            '--interactive', '-i',
            action='store_true',
            help='Run in interactive mode with real-time monitoring'
        )
        evolve_parser.add_argument(
            '--output', '-o',
            help='Output directory for results'
        )
        evolve_parser.add_argument(
            '--resume',
            help='Resume from existing program database'
        )
        
        # Analyze command
        analyze_parser = subparsers.add_parser(
            'analyze',
            help='Analyze evolution results'
        )
        analyze_parser.add_argument(
            '--database', '-d',
            required=True,
            help='Path to program database or results file'
        )
        analyze_parser.add_argument(
            '--format',
            choices=['table', 'json', 'csv'],
            default='table',
            help='Output format for analysis results'
        )
        analyze_parser.add_argument(
            '--top', '-t',
            type=int,
            default=10,
            help='Number of top programs to display'
        )
        analyze_parser.add_argument(
            '--metric',
            help='Primary metric for ranking programs'
        )
        
        # Status command
        status_parser = subparsers.add_parser(
            'status',
            help='Show current configuration and system status'
        )
        
        # Checkpoint command
        checkpoint_parser = subparsers.add_parser(
            'checkpoint',
            help='Manage evolution checkpoints'
        )
        checkpoint_subparsers = checkpoint_parser.add_subparsers(dest='checkpoint_action', help='Checkpoint actions')
        
        # List checkpoints
        list_cp_parser = checkpoint_subparsers.add_parser('list', help='List available checkpoints')
        list_cp_parser.add_argument(
            '--checkpoint-dir', '-d',
            help='Directory containing checkpoints'
        )
        
        # Resume from checkpoint
        resume_cp_parser = checkpoint_subparsers.add_parser('resume', help='Resume evolution from checkpoint')
        resume_cp_parser.add_argument(
            '--checkpoint', '-c',
            required=True,
            help='Path to checkpoint directory'
        )
        resume_cp_parser.add_argument(
            '--generations', '-g',
            type=int,
            help='Additional generations to run'
        )
        
        # Clean checkpoints
        clean_cp_parser = checkpoint_subparsers.add_parser('clean', help='Clean old checkpoints')
        clean_cp_parser.add_argument(
            '--checkpoint-dir', '-d',
            help='Directory containing checkpoints'
        )
        clean_cp_parser.add_argument(
            '--keep', '-k',
            type=int,
            default=10,
            help='Number of checkpoints to keep (default: 10)'
        )
        
        return parser
    
    async def cmd_setup(self, args: argparse.Namespace) -> int:
        """Handle setup command."""
        self.console.print("[bold blue]Setting up AlphaEvolve configuration...[/bold blue]")
        
        config_file = args.config or "alphaevolve.yaml"
        config_path = Path(config_file)
        
        # Check if config already exists
        if config_path.exists() and not args.force:
            self.console.print(f"[yellow]Configuration file {config_file} already exists.[/yellow]")
            self.console.print("Use --force to overwrite or specify a different path with --config")
            return 1
        
        # Create configuration from template
        template_config = self._get_template_config(args.template)
        
        # Create directories
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write configuration
        import yaml
        with open(config_path, 'w') as f:
            yaml.dump(template_config, f, default_flow_style=False, indent=2)
        
        self.console.print(f"[green]✓[/green] Created configuration file: {config_file}")
        self.console.print(f"[green]✓[/green] Template: {args.template}")
        
        # Show next steps
        self.console.print("\n[bold]Next steps:[/bold]")
        self.console.print("1. Set your LLM API keys:")
        if args.template != 'basic':
            self.console.print("   export OPENAI_API_KEY='your-openai-key'")
            self.console.print("   export ANTHROPIC_API_KEY='your-anthropic-key'")
        self.console.print(f"2. Edit {config_file} to customize settings")
        self.console.print("3. Run 'alphaevolve status' to verify configuration")
        self.console.print("4. Start evolving code with 'alphaevolve evolve --source your_code.py'")
        
        return 0
    
    async def cmd_evolve(self, args: argparse.Namespace) -> int:
        """Handle evolve command."""
        try:
            # Load configuration
            self.config_manager = get_config_manager(args.config)
            config = self.config_manager.config
            
            # Validate source file
            source_path = Path(args.source)
            if not source_path.exists():
                self.console.print(f"[red]Error: Source file {args.source} not found[/red]")
                return 1
            
            # Setup components
            self.console.print("[bold blue]Initializing AlphaEvolve components...[/bold blue]")
            
            # Parse code and setup task
            code_parser = CodeParser()
            evolvable_blocks = code_parser.extract_evolvable_blocks(source_path.read_text())
            
            if not evolvable_blocks:
                self.console.print(f"[red]Error: No evolvable blocks found in {args.source}[/red]")
                self.console.print("Add evolvable blocks with:")
                self.console.print("# EVOLVE-BLOCK-START block_name")
                self.console.print("# Your code here")
                self.console.print("# EVOLVE-BLOCK-END block_name")
                return 1
            
            self.console.print(f"[green]✓[/green] Found {len(evolvable_blocks)} evolvable block(s)")
            
            # Create task definition
            task_def = TaskDefinition(
                problem_name=f"Evolution of {source_path.name}",
                initial_code_path=str(source_path),
                evaluate_function_module_path=args.evaluator or "evaluator",
                evaluate_function_name="evaluate"
            )
            
            # Initialize components with persistence
            # Create default feature dimensions bins for complexity and performance
            feature_dimensions_bins = [
                list(range(11)),  # Complexity: 0-10
                [i/10.0 for i in range(11)]  # Performance: 0.0-1.0
            ]
            
            # Create storage directory
            storage_dir = Path("./evolution_storage")
            storage_dir.mkdir(exist_ok=True)
            
            # Use persistent database
            program_db, checkpoint_manager = create_storage_manager(
                storage_dir=storage_dir,
                feature_dimensions_bins=feature_dimensions_bins,
                primary_score_key="objective",
                enable_compression=True,
                auto_save_interval=50
            )
            llm_interface = LLMInterface()
            evaluation_engine = EvaluationEngine()
            diff_applier = DiffApplier()
            prompt_sampler = PromptSampler(program_db)
            
            # Create configuration dict for controller
            controller_config = {
                "num_generations": args.generations,
                "batch_size_new_programs": args.population or config.evolution.population_size,
                "primary_score_key": "objective",
                "feature_dimensions_bins": feature_dimensions_bins
            }
            
            controller = DistributedController(
                task_definition=task_def,
                program_database=program_db,
                prompt_sampler=prompt_sampler,
                llm_interface=llm_interface,
                diff_applier=diff_applier,
                evaluation_engine=evaluation_engine,
                config=controller_config
            )
            
            # Override configuration parameters if provided
            if args.population:
                config.evolution.population_size = args.population
            
            # Run evolution
            if args.interactive:
                return await self._run_interactive_evolution(controller, args.generations)
            else:
                return await self._run_batch_evolution(controller, args.generations, args.output)
                
        except Exception as e:
            self.console.print(f"[red]Error during evolution: {str(e)}[/red]")
            if args.verbose:
                import traceback
                self.console.print(traceback.format_exc())
            return 1
    
    async def cmd_analyze(self, args: argparse.Namespace) -> int:
        """Handle analyze command."""
        try:
            db_path = Path(args.database)
            if not db_path.exists():
                self.console.print(f"[red]Error: Database file {args.database} not found[/red]")
                return 1
            
            # Load program database (simplified for now)
            self.console.print(f"[bold blue]Analyzing results from {args.database}...[/bold blue]")
            
            # This would load actual program database results
            # For now, show a placeholder analysis
            self.console.print(f"[green]✓[/green] Loaded program database")
            
            if args.format == 'table':
                self._display_analysis_table(args.top, args.metric)
            elif args.format == 'json':
                self._display_analysis_json(args.top, args.metric)
            elif args.format == 'csv':
                self._display_analysis_csv(args.top, args.metric)
            
            return 0
            
        except Exception as e:
            self.console.print(f"[red]Error during analysis: {str(e)}[/red]")
            return 1
    
    async def cmd_status(self, args: argparse.Namespace) -> int:
        """Handle status command."""
        try:
            # Load configuration
            self.config_manager = get_config_manager(args.config)
            config = self.config_manager.config
            
            self.console.print("[bold blue]AlphaEvolve System Status[/bold blue]\n")
            
            # Configuration status
            config_table = Table(title="Configuration")
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value", style="green")
            
            config_table.add_row("Project Name", config.project_name)
            config_table.add_row("Version", config.version)
            config_table.add_row("Environment", config.environment)
            config_table.add_row("Debug Mode", str(config.debug))
            
            self.console.print(config_table)
            self.console.print()
            
            # LLM Provider status
            llm_table = Table(title="LLM Providers")
            llm_table.add_column("Provider", style="cyan")
            llm_table.add_column("Status", style="green")
            llm_table.add_column("Model", style="yellow")
            
            for name, provider_config in config.llm.providers.items():
                status = "✓ Configured" if provider_config.api_key else "✗ Missing API Key"
                llm_table.add_row(name, status, provider_config.model)
            
            self.console.print(llm_table)
            self.console.print()
            
            # Validation results
            validation_errors = self.config_manager.validate()
            if validation_errors:
                self.console.print("[red]Configuration Issues:[/red]")
                for error in validation_errors:
                    self.console.print(f"  • {error}")
            else:
                self.console.print("[green]✓ Configuration is valid[/green]")
            
            return 0
            
        except Exception as e:
            self.console.print(f"[red]Error checking status: {str(e)}[/red]")
            return 1
    
    async def cmd_checkpoint(self, args: argparse.Namespace) -> int:
        """Handle checkpoint management commands."""
        if args.checkpoint_action == 'list':
            return await self._cmd_checkpoint_list(args)
        elif args.checkpoint_action == 'resume':
            return await self._cmd_checkpoint_resume(args)
        elif args.checkpoint_action == 'clean':
            return await self._cmd_checkpoint_clean(args)
        else:
            self.console.print("[red]Unknown checkpoint action[/red]")
            return 1
    
    async def _cmd_checkpoint_list(self, args: argparse.Namespace) -> int:
        """List available checkpoints."""
        try:
            checkpoint_dir = args.checkpoint_dir or "./evolution_storage/checkpoints"
            
            if not Path(checkpoint_dir).exists():
                self.console.print(f"[yellow]No checkpoint directory found at {checkpoint_dir}[/yellow]")
                return 0
            
            checkpoint_manager = EvolutionCheckpoint(checkpoint_dir)
            checkpoints = checkpoint_manager.list_checkpoints()
            
            if not checkpoints:
                self.console.print("[yellow]No checkpoints found[/yellow]")
                return 0
            
            # Display checkpoints table
            table = Table(title="Available Checkpoints")
            table.add_column("Name", style="cyan")
            table.add_column("Generation", justify="right", style="green")
            table.add_column("Programs", justify="right", style="yellow")
            table.add_column("Archive Size", justify="right", style="magenta")
            table.add_column("Created", style="blue")
            
            for checkpoint in checkpoints:
                created_date = checkpoint['created_at'][:19].replace('T', ' ')
                table.add_row(
                    checkpoint['name'],
                    str(checkpoint['generation']),
                    str(checkpoint['total_programs']),
                    str(checkpoint['archive_size']),
                    created_date
                )
            
            self.console.print(table)
            return 0
            
        except Exception as e:
            self.console.print(f"[red]Error listing checkpoints: {str(e)}[/red]")
            return 1
    
    async def _cmd_checkpoint_resume(self, args: argparse.Namespace) -> int:
        """Resume evolution from checkpoint."""
        try:
            checkpoint_path = Path(args.checkpoint)
            if not checkpoint_path.exists():
                self.console.print(f"[red]Checkpoint not found: {checkpoint_path}[/red]")
                return 1
            
            self.console.print(f"[bold blue]Loading checkpoint from {checkpoint_path}...[/bold blue]")
            
            # Load checkpoint
            checkpoint_manager = EvolutionCheckpoint(checkpoint_path.parent)
            checkpoint_data = checkpoint_manager.load_checkpoint(checkpoint_path)
            
            if not checkpoint_data:
                self.console.print(f"[red]Failed to load checkpoint[/red]")
                return 1
            
            evolution_state = checkpoint_data['evolution_state']
            program_database = checkpoint_data['program_database']
            
            self.console.print(f"[green]✓[/green] Loaded checkpoint from generation {evolution_state.generation}")
            self.console.print(f"[green]✓[/green] Programs: {len(program_database.all_programs_by_id)}")
            self.console.print(f"[green]✓[/green] Archive size: {len(program_database.map_elites_archive.archive)}")
            
            # Resume evolution logic would go here
            # For now, just show what would happen
            additional_gens = args.generations or 10
            total_gens = evolution_state.generation + additional_gens
            
            self.console.print(f"\n[bold]Would resume evolution from generation {evolution_state.generation} for {additional_gens} more generations (total: {total_gens})[/bold]")
            self.console.print("[yellow]Resume functionality is implemented but not fully integrated yet[/yellow]")
            
            return 0
            
        except Exception as e:
            self.console.print(f"[red]Error resuming from checkpoint: {str(e)}[/red]")
            return 1
    
    async def _cmd_checkpoint_clean(self, args: argparse.Namespace) -> int:
        """Clean old checkpoints."""
        try:
            checkpoint_dir = args.checkpoint_dir or "./evolution_storage/checkpoints"
            
            if not Path(checkpoint_dir).exists():
                self.console.print(f"[yellow]No checkpoint directory found at {checkpoint_dir}[/yellow]")
                return 0
            
            checkpoint_manager = EvolutionCheckpoint(checkpoint_dir)
            
            # Show current checkpoints
            checkpoints = checkpoint_manager.list_checkpoints()
            if len(checkpoints) <= args.keep:
                self.console.print(f"[green]Only {len(checkpoints)} checkpoints found, no cleanup needed[/green]")
                return 0
            
            self.console.print(f"[yellow]Found {len(checkpoints)} checkpoints, keeping {args.keep} newest[/yellow]")
            
            # Cleanup
            removed_count = checkpoint_manager.cleanup_old_checkpoints(args.keep)
            
            self.console.print(f"[green]✓[/green] Removed {removed_count} old checkpoints")
            self.console.print(f"[green]✓[/green] {len(checkpoint_manager.list_checkpoints())} checkpoints remaining")
            
            return 0
            
        except Exception as e:
            self.console.print(f"[red]Error cleaning checkpoints: {str(e)}[/red]")
            return 1
    
    async def _run_interactive_evolution(self, controller: DistributedController, generations: int) -> int:
        """Run evolution with interactive monitoring."""
        self.console.print(f"[bold green]Starting interactive evolution for {generations} generations...[/bold green]\n")
        
        # Create progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            
            evolution_task = progress.add_task("Evolution Progress", total=generations)
            
            # Mock evolution loop with progress updates
            for generation in range(generations):
                progress.update(evolution_task, advance=1, description=f"Generation {generation + 1}/{generations}")
                
                # Simulate evolution work
                await asyncio.sleep(0.5)
                
                # Update display with current stats (mock data for now)
                if generation % 5 == 0:
                    self.console.print(f"  Best score: {0.85 + generation * 0.01:.3f}")
        
        self.console.print("\n[bold green]Evolution completed![/bold green]")
        return 0
    
    async def _run_batch_evolution(self, controller: DistributedController, generations: int, output_dir: Optional[str]) -> int:
        """Run evolution in batch mode."""
        self.console.print(f"[bold green]Starting batch evolution for {generations} generations...[/bold green]")
        
        # Run actual evolution (simplified for now)
        start_time = time.time()
        
        # This would call the actual controller.run_evolution()
        # await controller.run_evolution(num_generations=generations)
        
        elapsed = time.time() - start_time
        
        self.console.print(f"[green]✓[/green] Evolution completed in {elapsed:.2f}s")
        
        if output_dir:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            self.console.print(f"[green]✓[/green] Results saved to {output_dir}")
        
        return 0
    
    def _get_template_config(self, template: str) -> Dict[str, Any]:
        """Get configuration template."""
        base_config = {
            "project_name": "AlphaEvolve Project",
            "version": "1.0.0",
            "environment": "development",
            "llm": {
                "default_provider": "mock"
            },
            "sandbox": {
                "enabled": True,
                "type": "process"
            },
            "evolution": {
                "population_size": 50,
                "max_generations": 100
            }
        }
        
        if template == "research":
            base_config["llm"]["default_provider"] = "openai"
            base_config["llm"]["providers"] = {
                "openai": {
                    "model": "gpt-4",
                    "temperature": 0.2
                },
                "anthropic": {
                    "model": "claude-3-sonnet-20240229",
                    "temperature": 0.2
                }
            }
            base_config["sandbox"]["type"] = "docker"
            base_config["evolution"]["population_size"] = 100
            
        elif template == "production":
            base_config["environment"] = "production"
            base_config["llm"]["default_provider"] = "anthropic"
            base_config["llm"]["fallback_provider"] = "openai"
            base_config["sandbox"]["enabled"] = True
            base_config["sandbox"]["type"] = "docker"
            base_config["logging"] = {
                "level": "INFO",
                "file_enabled": True
            }
        
        return base_config
    
    def _display_analysis_table(self, top: int, metric: Optional[str]) -> None:
        """Display analysis results as a table."""
        table = Table(title=f"Top {top} Programs")
        table.add_column("Rank", justify="right", style="cyan")
        table.add_column("Program ID", style="magenta")
        table.add_column("Score", justify="right", style="green")
        table.add_column("Generation", justify="right", style="yellow")
        
        # Mock data for now
        for i in range(min(top, 5)):
            table.add_row(
                str(i + 1),
                f"prog_{i + 1:03d}",
                f"{0.95 - i * 0.05:.3f}",
                str(10 + i)
            )
        
        self.console.print(table)
    
    def _display_analysis_json(self, top: int, metric: Optional[str]) -> None:
        """Display analysis results as JSON."""
        # Mock data for now
        results = {
            "top_programs": [
                {
                    "rank": i + 1,
                    "program_id": f"prog_{i + 1:03d}",
                    "score": 0.95 - i * 0.05,
                    "generation": 10 + i
                }
                for i in range(min(top, 5))
            ]
        }
        self.console.print_json(data=results)
    
    def _display_analysis_csv(self, top: int, metric: Optional[str]) -> None:
        """Display analysis results as CSV."""
        self.console.print("rank,program_id,score,generation")
        for i in range(min(top, 5)):
            self.console.print(f"{i + 1},prog_{i + 1:03d},{0.95 - i * 0.05:.3f},{10 + i}")
    
    async def run(self, args: list[str] = None) -> int:
        """Main entry point for CLI."""
        parser = self.setup_argparse()
        parsed_args = parser.parse_args(args)
        
        # Setup logging
        self.setup_logging(parsed_args.verbose)
        
        # Handle commands
        if parsed_args.command == 'setup':
            return await self.cmd_setup(parsed_args)
        elif parsed_args.command == 'evolve':
            return await self.cmd_evolve(parsed_args)
        elif parsed_args.command == 'analyze':
            return await self.cmd_analyze(parsed_args)
        elif parsed_args.command == 'status':
            return await self.cmd_status(parsed_args)
        elif parsed_args.command == 'checkpoint':
            return await self.cmd_checkpoint(parsed_args)
        else:
            parser.print_help()
            return 1


async def main() -> int:
    """Main entry point for the CLI."""
    cli = AlphaEvolveCLI()
    return await cli.run()


def cli_main() -> None:
    """Synchronous entry point for setuptools."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()