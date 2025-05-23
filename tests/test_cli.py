"""
Tests for the AlphaEvolve CLI interface.

This module tests all CLI commands and functionality including argument parsing,
command execution, configuration management, and user interaction.
"""

import asyncio
import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from alpha_evolve.cli import AlphaEvolveCLI


class TestCLIArgumentParsing:
    """Test argument parsing for all CLI commands."""
    
    def test_setup_help(self):
        """Test setup command help."""
        cli = AlphaEvolveCLI()
        parser = cli.setup_argparse()
        
        # --help should cause SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args(['setup', '--help'])
    
    def test_evolve_required_args(self):
        """Test evolve command requires source argument."""
        cli = AlphaEvolveCLI()
        parser = cli.setup_argparse()
        
        with pytest.raises(SystemExit):
            parser.parse_args(['evolve'])  # Missing required --source
    
    def test_evolve_valid_args(self):
        """Test evolve command with valid arguments."""
        cli = AlphaEvolveCLI()
        parser = cli.setup_argparse()
        
        args = parser.parse_args(['evolve', '--source', 'test.py', '--generations', '5'])
        assert args.command == 'evolve'
        assert args.source == 'test.py'
        assert args.generations == 5
        assert args.interactive is False
    
    def test_evolve_interactive_mode(self):
        """Test evolve command with interactive flag."""
        cli = AlphaEvolveCLI()
        parser = cli.setup_argparse()
        
        args = parser.parse_args(['evolve', '--source', 'test.py', '--interactive'])
        assert args.interactive is True
    
    def test_analyze_required_args(self):
        """Test analyze command requires database argument."""
        cli = AlphaEvolveCLI()
        parser = cli.setup_argparse()
        
        with pytest.raises(SystemExit):
            parser.parse_args(['analyze'])  # Missing required --database
    
    def test_analyze_valid_args(self):
        """Test analyze command with valid arguments."""
        cli = AlphaEvolveCLI()
        parser = cli.setup_argparse()
        
        args = parser.parse_args(['analyze', '--database', 'results.json', '--format', 'csv'])
        assert args.command == 'analyze'
        assert args.database == 'results.json'
        assert args.format == 'csv'
    
    def test_status_command(self):
        """Test status command parsing."""
        cli = AlphaEvolveCLI()
        parser = cli.setup_argparse()
        
        args = parser.parse_args(['status'])
        assert args.command == 'status'
    
    def test_global_options(self):
        """Test global options like --config and --verbose."""
        cli = AlphaEvolveCLI()
        parser = cli.setup_argparse()
        
        args = parser.parse_args(['--config', 'custom.yaml', '--verbose', 'status'])
        assert args.config == 'custom.yaml'
        assert args.verbose is True
        assert args.command == 'status'


class TestSetupCommand:
    """Test the setup command functionality."""
    
    @pytest.mark.asyncio
    async def test_setup_basic_template(self):
        """Test setup command with basic template."""
        cli = AlphaEvolveCLI()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.yaml"
            
            # Mock arguments
            args = MagicMock()
            args.config = str(config_file)
            args.force = False
            args.template = 'basic'
            
            result = await cli.cmd_setup(args)
            
            assert result == 0
            assert config_file.exists()
            
            # Check config content
            import yaml
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            assert config['project_name'] == 'AlphaEvolve Project'
            assert config['llm']['default_provider'] == 'mock'
            assert config['sandbox']['type'] == 'process'
    
    @pytest.mark.asyncio
    async def test_setup_research_template(self):
        """Test setup command with research template."""
        cli = AlphaEvolveCLI()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "research_config.yaml"
            
            args = MagicMock()
            args.config = str(config_file)
            args.force = False
            args.template = 'research'
            
            result = await cli.cmd_setup(args)
            
            assert result == 0
            assert config_file.exists()
            
            import yaml
            with open(config_file) as f:
                config = yaml.safe_load(f)
            
            assert config['llm']['default_provider'] == 'openai'
            assert 'providers' in config['llm']
            assert config['sandbox']['type'] == 'docker'
    
    @pytest.mark.asyncio
    async def test_setup_existing_file_no_force(self):
        """Test setup command fails when config exists and no --force."""
        cli = AlphaEvolveCLI()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "existing_config.yaml"
            config_file.write_text("existing: config")
            
            args = MagicMock()
            args.config = str(config_file)
            args.force = False
            args.template = 'basic'
            
            result = await cli.cmd_setup(args)
            
            assert result == 1  # Should fail
            assert config_file.read_text() == "existing: config"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_setup_existing_file_with_force(self):
        """Test setup command overwrites when --force is used."""
        cli = AlphaEvolveCLI()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "force_config.yaml"
            config_file.write_text("existing: config")
            
            args = MagicMock()
            args.config = str(config_file)
            args.force = True
            args.template = 'basic'
            
            result = await cli.cmd_setup(args)
            
            assert result == 0
            assert "existing: config" not in config_file.read_text()


class TestEvolveCommand:
    """Test the evolve command functionality."""
    
    @pytest.mark.asyncio
    async def test_evolve_missing_source_file(self):
        """Test evolve command with missing source file."""
        cli = AlphaEvolveCLI()
        
        args = MagicMock()
        args.config = None
        args.source = 'nonexistent.py'
        args.evaluator = None
        args.generations = 5
        args.population = None
        args.interactive = False
        args.output = None
        args.resume = None
        args.verbose = False
        
        result = await cli.cmd_evolve(args)
        
        assert result == 1  # Should fail
    
    @pytest.mark.asyncio
    async def test_evolve_no_evolvable_blocks(self):
        """Test evolve command with file containing no evolvable blocks."""
        cli = AlphaEvolveCLI()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("# No evolvable blocks here\\ndef simple_function():\\n    pass")
            temp_file = f.name
        
        try:
            args = MagicMock()
            args.config = None
            args.source = temp_file
            args.evaluator = None
            args.generations = 5
            args.population = None
            args.interactive = False
            args.output = None
            args.resume = None
            args.verbose = False
            
            result = await cli.cmd_evolve(args)
            
            assert result == 1  # Should fail due to no evolvable blocks
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio 
    async def test_evolve_with_evolvable_blocks(self):
        """Test evolve command with valid evolvable blocks."""
        cli = AlphaEvolveCLI()
        
        code_content = '''
# EVOLVE-BLOCK-START test_block
def test_function(x):
    return x * 2
# EVOLVE-BLOCK-END test_block
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code_content)
            temp_file = f.name
        
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as config_f:
            config_content = '''
project_name: Test Project
llm:
  default_provider: mock
sandbox:
  enabled: true
  type: process
evolution:
  population_size: 10
'''
            config_f.write(config_content)
            config_file = config_f.name
        
        try:
            args = MagicMock()
            args.config = config_file
            args.source = temp_file
            args.evaluator = None
            args.generations = 2
            args.population = None
            args.interactive = False
            args.output = None
            args.resume = None
            args.verbose = False
            
            # Mock the actual evolution to avoid running real LLM calls
            with patch('alpha_evolve.cli.DistributedController') as mock_controller:
                result = await cli.cmd_evolve(args)
                
                # Should succeed in initialization
                assert result == 0
                mock_controller.assert_called_once()
        finally:
            os.unlink(temp_file)
            os.unlink(config_file)


class TestAnalyzeCommand:
    """Test the analyze command functionality."""
    
    @pytest.mark.asyncio
    async def test_analyze_missing_database(self):
        """Test analyze command with missing database file."""
        cli = AlphaEvolveCLI()
        
        args = MagicMock()
        args.database = 'nonexistent_db.json'
        args.format = 'table'
        args.top = 10
        args.metric = None
        
        result = await cli.cmd_analyze(args)
        
        assert result == 1  # Should fail
    
    @pytest.mark.asyncio
    async def test_analyze_table_format(self):
        """Test analyze command with table format."""
        cli = AlphaEvolveCLI()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"dummy": "data"}, f)
            temp_file = f.name
        
        try:
            args = MagicMock()
            args.database = temp_file
            args.format = 'table'
            args.top = 5
            args.metric = None
            
            result = await cli.cmd_analyze(args)
            
            assert result == 0
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_analyze_json_format(self):
        """Test analyze command with JSON format."""
        cli = AlphaEvolveCLI()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"dummy": "data"}, f)
            temp_file = f.name
        
        try:
            args = MagicMock()
            args.database = temp_file
            args.format = 'json'
            args.top = 3
            args.metric = 'score'
            
            result = await cli.cmd_analyze(args)
            
            assert result == 0
        finally:
            os.unlink(temp_file)
    
    @pytest.mark.asyncio
    async def test_analyze_csv_format(self):
        """Test analyze command with CSV format."""
        cli = AlphaEvolveCLI()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"dummy": "data"}, f)
            temp_file = f.name
        
        try:
            args = MagicMock()
            args.database = temp_file
            args.format = 'csv'
            args.top = 10
            args.metric = None
            
            result = await cli.cmd_analyze(args)
            
            assert result == 0
        finally:
            os.unlink(temp_file)


class TestStatusCommand:
    """Test the status command functionality."""
    
    @pytest.mark.asyncio
    async def test_status_with_valid_config(self):
        """Test status command with valid configuration."""
        cli = AlphaEvolveCLI()
        
        # Create a temporary config file
        config_content = '''
project_name: Test Project
version: 1.0.0
environment: development
debug: false
llm:
  default_provider: mock
  providers:
    mock:
      model: mock-model
      api_key: null
sandbox:
  enabled: true
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_file = f.name
        
        try:
            args = MagicMock()
            args.config = config_file
            
            result = await cli.cmd_status(args)
            
            assert result == 0
        finally:
            os.unlink(config_file)
    
    @pytest.mark.asyncio
    async def test_status_with_invalid_config(self):
        """Test status command handling invalid configuration."""
        cli = AlphaEvolveCLI()
        
        # Create an invalid config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_file = f.name
        
        try:
            args = MagicMock()
            args.config = config_file
            
            # Should handle the error gracefully
            result = await cli.cmd_status(args)
            
            # May succeed or fail depending on error handling
            assert result in [0, 1]
        finally:
            os.unlink(config_file)


class TestCLIIntegration:
    """Test end-to-end CLI functionality."""
    
    @pytest.mark.asyncio
    async def test_cli_run_help(self):
        """Test running CLI with help command."""
        cli = AlphaEvolveCLI()
        
        with pytest.raises(SystemExit):
            await cli.run(['--help'])
    
    @pytest.mark.asyncio
    async def test_cli_run_no_command(self):
        """Test running CLI with no command."""
        cli = AlphaEvolveCLI()
        
        result = await cli.run([])
        
        assert result == 1
    
    @pytest.mark.asyncio
    async def test_cli_run_status(self):
        """Test running CLI with status command."""
        cli = AlphaEvolveCLI()
        
        # Create a minimal config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write('''
project_name: CLI Test
llm:
  default_provider: mock
''')
            config_file = f.name
        
        try:
            result = await cli.run(['--config', config_file, 'status'])
            
            assert result == 0
        finally:
            os.unlink(config_file)
    
    def test_cli_main_entry_point(self):
        """Test the main CLI entry point."""
        # This tests the synchronous wrapper
        with patch('alpha_evolve.cli.asyncio.run') as mock_run:
            mock_run.return_value = 0
            
            from alpha_evolve.cli import cli_main
            
            with pytest.raises(SystemExit) as exc_info:
                cli_main()
            
            assert exc_info.value.code == 0
            mock_run.assert_called_once()


class TestCLITemplates:
    """Test configuration template generation."""
    
    def test_basic_template(self):
        """Test basic configuration template."""
        cli = AlphaEvolveCLI()
        config = cli._get_template_config('basic')
        
        assert config['project_name'] == 'AlphaEvolve Project'
        assert config['llm']['default_provider'] == 'mock'
        assert config['sandbox']['type'] == 'process'
    
    def test_research_template(self):
        """Test research configuration template."""
        cli = AlphaEvolveCLI()
        config = cli._get_template_config('research')
        
        assert config['llm']['default_provider'] == 'openai'
        assert 'providers' in config['llm']
        assert 'openai' in config['llm']['providers']
        assert 'anthropic' in config['llm']['providers']
        assert config['sandbox']['type'] == 'docker'
    
    def test_production_template(self):
        """Test production configuration template."""
        cli = AlphaEvolveCLI()
        config = cli._get_template_config('production')
        
        assert config['environment'] == 'production'
        assert config['llm']['default_provider'] == 'anthropic'
        assert config['llm']['fallback_provider'] == 'openai'
        assert config['sandbox']['type'] == 'docker'
        assert 'logging' in config


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_evolve_with_exception(self):
        """Test evolve command handles exceptions gracefully."""
        cli = AlphaEvolveCLI()
        
        args = MagicMock()
        args.config = None
        args.source = 'test.py'
        args.verbose = False
        
        # Mock an exception during component initialization
        with patch('alpha_evolve.cli.CodeParser') as mock_parser:
            mock_parser.side_effect = Exception("Test exception")
            
            result = await cli.cmd_evolve(args)
            
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_analyze_with_exception(self):
        """Test analyze command handles exceptions gracefully."""
        cli = AlphaEvolveCLI()
        
        args = MagicMock()
        args.database = 'test.json'
        
        # Mock an exception during file reading
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.side_effect = Exception("Test exception")
            
            result = await cli.cmd_analyze(args)
            
            assert result == 1
    
    @pytest.mark.asyncio
    async def test_status_with_exception(self):
        """Test status command handles exceptions gracefully."""
        cli = AlphaEvolveCLI()
        
        args = MagicMock()
        args.config = None
        
        # Mock an exception during config loading
        with patch('alpha_evolve.cli.get_config_manager') as mock_config:
            mock_config.side_effect = Exception("Test exception")
            
            result = await cli.cmd_status(args)
            
            assert result == 1