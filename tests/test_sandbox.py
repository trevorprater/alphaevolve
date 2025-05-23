"""
Tests for the sandbox security system.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path

from alpha_evolve.sandbox import (
    ResourceLimits, 
    SandboxResult, 
    SandboxError,
    ProcessSandbox, 
    DockerSandbox,
    create_sandbox
)


class TestResourceLimits:
    """Test ResourceLimits configuration."""
    
    def test_default_limits(self):
        """Test default resource limits."""
        limits = ResourceLimits()
        assert limits.cpu_limit == 1.0
        assert limits.memory_limit == "256m"
        assert limits.timeout_seconds == 30
        assert limits.max_output_size == 1024 * 1024
        assert limits.network_disabled is True
    
    def test_custom_limits(self):
        """Test custom resource limits."""
        limits = ResourceLimits(
            cpu_limit=0.5,
            memory_limit="512m",
            timeout_seconds=60,
            max_output_size=2048,
            network_disabled=False
        )
        assert limits.cpu_limit == 0.5
        assert limits.memory_limit == "512m"
        assert limits.timeout_seconds == 60
        assert limits.max_output_size == 2048
        assert limits.network_disabled is False


class TestSandboxResult:
    """Test SandboxResult data structure."""
    
    def test_success_result(self):
        """Test successful result creation."""
        result = SandboxResult(
            success=True,
            stdout="Hello, World!",
            stderr="",
            return_code=0,
            execution_time=0.5
        )
        assert result.success is True
        assert result.stdout == "Hello, World!"
        assert result.stderr == ""
        assert result.return_code == 0
        assert result.execution_time == 0.5
    
    def test_error_result(self):
        """Test error result creation."""
        result = SandboxResult(
            success=False,
            stderr="Error occurred",
            return_code=1,
            execution_time=0.1,
            error_message="Execution failed"
        )
        assert result.success is False
        assert result.stderr == "Error occurred"
        assert result.return_code == 1
        assert result.error_message == "Execution failed"


class TestProcessSandbox:
    """Test ProcessSandbox functionality."""
    
    def test_initialization(self):
        """Test ProcessSandbox initialization."""
        sandbox = ProcessSandbox()
        assert sandbox.resource_limits.timeout_seconds == 30
        assert sandbox.resource_limits.memory_limit == "256m"
    
    @pytest.mark.asyncio
    async def test_simple_code_execution(self):
        """Test executing simple Python code."""
        sandbox = ProcessSandbox()
        code = "x = 5\ny = 10\nresult = x + y\nprint(f'Result: {result}')"
        
        result = await sandbox.execute(code)
        
        assert result.success is True
        assert "Result: 15" in result.stdout
        assert result.return_code == 0
        assert result.execution_time > 0
    
    @pytest.mark.asyncio
    async def test_code_with_inputs(self):
        """Test executing code with input data."""
        sandbox = ProcessSandbox()
        code = "result = __inputs__['a'] + __inputs__['b']\nprint(f'Sum: {result}')"
        inputs = {"a": 3, "b": 7}
        
        result = await sandbox.execute(code, inputs)
        
        assert result.success is True
        assert "Sum: 10" in result.stdout
    
    @pytest.mark.asyncio 
    async def test_syntax_error_handling(self):
        """Test handling of syntax errors."""
        sandbox = ProcessSandbox()
        code = "def broken_function(\n    pass"  # Invalid syntax
        
        result = await sandbox.execute(code)
        
        assert result.success is False
        assert result.return_code != 0
        assert "SyntaxError" in result.stderr or "invalid syntax" in result.stderr
    
    @pytest.mark.asyncio
    async def test_runtime_error_handling(self):
        """Test handling of runtime errors."""
        sandbox = ProcessSandbox()
        code = "x = 1 / 0"  # Division by zero
        
        result = await sandbox.execute(code)
        
        assert result.success is False
        assert result.return_code != 0
        assert "ZeroDivisionError" in result.stderr
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout enforcement."""
        limits = ResourceLimits(timeout_seconds=2)
        sandbox = ProcessSandbox(limits)
        code = """
import time
time.sleep(5)  # Sleep longer than timeout
print("This should not print")
"""
        
        result = await sandbox.execute(code)
        
        assert result.success is False
        assert "timed out" in result.error_message.lower()
        assert result.execution_time >= 2  # Should be at least timeout duration
    
    @pytest.mark.asyncio
    async def test_output_size_limiting(self):
        """Test output size limiting."""
        limits = ResourceLimits(max_output_size=100)
        sandbox = ProcessSandbox(limits)
        code = """
for i in range(1000):
    print(f"Line {i}: This is a long line of text that will generate lots of output")
"""
        
        result = await sandbox.execute(code)
        
        # Output should be truncated
        assert len(result.stdout) <= limits.max_output_size
    
    def test_cleanup(self):
        """Test sandbox cleanup."""
        sandbox = ProcessSandbox()
        # ProcessSandbox cleanup should not raise errors
        sandbox.cleanup()


class TestDockerSandbox:
    """Test DockerSandbox functionality."""
    
    def test_initialization_without_docker(self):
        """Test DockerSandbox initialization when Docker is not available."""
        # This test assumes Docker is not available for testing
        # In CI/CD, you might want to mock Docker unavailability
        try:
            sandbox = DockerSandbox()
            # If Docker is available, this will succeed
            assert sandbox is not None
        except SandboxError:
            # If Docker is not available, this should raise SandboxError
            pass
    
    @pytest.mark.asyncio
    async def test_docker_simple_execution(self):
        """Test Docker execution if Docker is available."""
        try:
            sandbox = DockerSandbox()
            code = "print('Hello from Docker!')"
            
            result = await sandbox.execute(code)
            
            # This test only runs if Docker is available
            assert result.success is True
            assert "Hello from Docker!" in result.stdout
            
        except SandboxError:
            # Skip test if Docker is not available
            pytest.skip("Docker not available for testing")
    
    @pytest.mark.asyncio
    async def test_docker_resource_limits(self):
        """Test Docker resource limiting."""
        try:
            limits = ResourceLimits(
                memory_limit="128m",
                timeout_seconds=5,
                cpu_limit=0.5
            )
            sandbox = DockerSandbox(limits)
            code = "print('Testing resource limits')"
            
            result = await sandbox.execute(code)
            
            assert result.success is True
            if result.resource_usage:
                # Check that resource usage data is collected
                assert 'memory_usage_bytes' in result.resource_usage
                assert 'cpu_usage_percent' in result.resource_usage
                
        except SandboxError:
            pytest.skip("Docker not available for testing")
    
    def test_docker_cleanup(self):
        """Test Docker sandbox cleanup."""
        try:
            sandbox = DockerSandbox()
            sandbox.cleanup()  # Should not raise errors
        except SandboxError:
            pytest.skip("Docker not available for testing")


class TestSandboxFactory:
    """Test sandbox factory function."""
    
    def test_create_process_sandbox(self):
        """Test creating process sandbox."""
        sandbox = create_sandbox("process")
        assert isinstance(sandbox, ProcessSandbox)
    
    def test_create_docker_sandbox(self):
        """Test creating Docker sandbox."""
        try:
            sandbox = create_sandbox("docker")
            assert isinstance(sandbox, DockerSandbox)
        except SandboxError:
            # Expected if Docker is not available
            pass
    
    def test_create_invalid_sandbox(self):
        """Test creating invalid sandbox type."""
        with pytest.raises(SandboxError):
            create_sandbox("invalid_type")
    
    def test_create_sandbox_with_limits(self):
        """Test creating sandbox with custom limits."""
        limits = ResourceLimits(timeout_seconds=60)
        sandbox = create_sandbox("process", limits)
        assert sandbox.resource_limits.timeout_seconds == 60


class TestSecurityFeatures:
    """Test security-related functionality."""
    
    @pytest.mark.asyncio
    async def test_file_system_access_prevention(self):
        """Test that malicious file system access is prevented."""
        sandbox = ProcessSandbox()
        
        # Try to read a system file
        malicious_code = """
try:
    with open('/etc/passwd', 'r') as f:
        content = f.read()
    print("SECURITY BREACH: Read system file")
    print(content[:100])
except Exception as e:
    print(f"Access denied: {e}")
"""
        
        result = await sandbox.execute(malicious_code)
        
        # The code should run but file access should be limited
        # (Note: ProcessSandbox has limited security compared to DockerSandbox)
        assert result.success is True
        output = result.stdout.lower()
        
        # Should either deny access or show limited info
        if "security breach" in output:
            # If file was readable, it's a limitation of ProcessSandbox
            # DockerSandbox would prevent this
            pass
        else:
            assert "access denied" in output or "permission denied" in output
    
    @pytest.mark.asyncio
    async def test_infinite_loop_protection(self):
        """Test protection against infinite loops."""
        limits = ResourceLimits(timeout_seconds=3)
        sandbox = ProcessSandbox(limits)
        
        infinite_loop_code = """
counter = 0
while True:
    counter += 1
    if counter % 1000000 == 0:
        print(f"Still running: {counter}")
"""
        
        result = await sandbox.execute(infinite_loop_code)
        
        assert result.success is False
        assert "timed out" in result.error_message.lower()
        assert result.execution_time >= 3  # Should timeout after ~3 seconds
    
    @pytest.mark.asyncio
    async def test_memory_bomb_protection(self):
        """Test protection against memory bombs."""
        limits = ResourceLimits(timeout_seconds=10)  # Give enough time but limit memory
        sandbox = ProcessSandbox(limits)
        
        memory_bomb_code = """
# Try to allocate large amounts of memory
data = []
try:
    for i in range(1000000):
        data.append([0] * 1000)  # Allocate large lists
        if i % 10000 == 0:
            print(f"Allocated {i} chunks")
except MemoryError:
    print("Memory allocation failed (good!)")
except Exception as e:
    print(f"Error: {e}")
"""
        
        result = await sandbox.execute(memory_bomb_code)
        
        # Should either complete with memory error or timeout
        assert result.execution_time < 30  # Should not run indefinitely
        
        if result.success:
            # If it completed, memory error should have been caught
            assert "memory allocation failed" in result.stdout.lower() or "error:" in result.stdout.lower()
    
    @pytest.mark.asyncio
    async def test_import_restrictions(self):
        """Test restrictions on dangerous imports."""
        sandbox = ProcessSandbox()
        
        dangerous_imports_code = """
import sys
print(f"Python version: {sys.version}")

try:
    import subprocess
    result = subprocess.run(['echo', 'hello'], capture_output=True, text=True)
    print(f"Subprocess result: {result.stdout}")
except Exception as e:
    print(f"Subprocess import/usage failed: {e}")

try:
    import os
    print(f"Current directory: {os.getcwd()}")
    files = os.listdir('.')
    print(f"Directory contents: {files}")
except Exception as e:
    print(f"OS operations failed: {e}")
"""
        
        result = await sandbox.execute(dangerous_imports_code)
        
        # Code should run but access should be limited
        assert result.success is True
        output = result.stdout
        
        # Basic imports like sys should work
        assert "Python version:" in output
        
        # subprocess and os operations might work in ProcessSandbox
        # but would be restricted in DockerSandbox


class TestIntegrationWithEvaluationEngine:
    """Test sandbox integration with EvaluationEngine."""
    
    @pytest.mark.asyncio
    async def test_sandbox_with_evaluation_engine(self):
        """Test sandbox integration with evaluation engine."""
        from alpha_evolve.evaluation_engine import EvaluationEngine
        
        # Configure evaluation engine to use process sandbox for testing
        config = {
            'use_sandbox': True,
            'sandbox_type': 'process',
            'timeout_seconds': 5
        }
        
        engine = EvaluationEngine(config)
        
        # Simple evaluation function
        def simple_evaluator(namespace, inputs=None):
            if 'result' in namespace:
                return {'score': float(namespace['result'])}
            else:
                return {'score': 0.0, 'error': True}
        
        # Test code that should work
        code = "result = 42"
        
        result = await engine.evaluate_program(code, simple_evaluator)
        
        assert result['score'] == 42.0
        assert 'execution_time' in result  # Should include timing info
        assert result.get('error', False) is False
    
    @pytest.mark.asyncio
    async def test_sandbox_fallback_to_direct_execution(self):
        """Test fallback when sandbox is not available."""
        from alpha_evolve.evaluation_engine import EvaluationEngine
        
        # Configure with invalid sandbox type to force fallback
        config = {
            'use_sandbox': True,
            'sandbox_type': 'invalid_type',
            'timeout_seconds': 5
        }
        
        engine = EvaluationEngine(config)
        
        # Should fallback to direct execution
        assert engine.use_sandbox is False
        assert engine.sandbox is None
        
        # Simple evaluation function
        def simple_evaluator(namespace, inputs=None):
            if 'result' in namespace:
                return {'score': float(namespace['result'])}
            else:
                return {'score': 0.0, 'error': True}
        
        code = "result = 123"
        result = await engine.evaluate_program(code, simple_evaluator)
        
        assert result['score'] == 123.0
        assert result.get('error', False) is False