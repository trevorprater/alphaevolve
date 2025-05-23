#!/usr/bin/env python3
"""
SDK Integration Test Script

This script installs optional LLM SDK packages and runs comprehensive tests
to verify they work correctly with the AlphaEvolve LLM interface.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path


def run_command(cmd, capture_output=True, check=True):
    """Run a command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(
        cmd, 
        shell=True, 
        capture_output=capture_output, 
        text=True, 
        check=check
    )
    if capture_output and result.stdout:
        print(result.stdout)
    if capture_output and result.stderr:
        print(result.stderr)
    return result


def check_package_installed(package_name):
    """Check if a package is installed."""
    try:
        result = run_command(f"python -c 'import {package_name}'", check=False)
        return result.returncode == 0
    except:
        return False


def install_sdk_packages():
    """Install all LLM SDK packages."""
    print("🔧 Installing LLM SDK packages...")
    
    packages = [
        "openai>=1.54.0",
        "anthropic>=0.39.0", 
        "google-genai>=0.8.0",
        "google-cloud-aiplatform>=1.70.0"
    ]
    
    for package in packages:
        try:
            print(f"\n📦 Installing {package}...")
            run_command(f"uv pip install '{package}'", capture_output=False)
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package}: {e}")
            return False
    
    print("\n✅ All SDK packages installed successfully!")
    return True


def verify_imports():
    """Verify all SDK packages can be imported."""
    print("\n🔍 Verifying SDK imports...")
    
    imports = [
        ("openai", "OpenAI SDK"),
        ("anthropic", "Anthropic SDK"),
        ("google.genai", "Google Genai SDK"),
        ("google.cloud.aiplatform", "Vertex AI SDK")
    ]
    
    success = True
    for import_name, display_name in imports:
        try:
            run_command(f"python -c 'import {import_name}; print(f\"{display_name}: OK\")'", capture_output=False)
        except subprocess.CalledProcessError:
            print(f"❌ Failed to import {display_name}")
            success = False
    
    return success


def run_sdk_tests():
    """Run the SDK integration tests."""
    print("\n🧪 Running SDK integration tests...")
    
    try:
        # Run our new SDK integration tests
        result = run_command(
            "python -m pytest tests/test_sdk_integration.py -v -s", 
            capture_output=False
        )
        
        print("\n🧪 Running existing LLM interface tests...")
        result = run_command(
            "python -m pytest tests/test_llm_interface.py -v", 
            capture_output=False
        )
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Tests failed: {e}")
        return False


def test_real_api_calls():
    """Test with real API calls if keys are available."""
    print("\n🌐 Testing real API calls (if keys available)...")
    
    # Check which API keys are available
    api_keys = {
        'OPENAI_API_KEY': 'OpenAI',
        'ANTHROPIC_API_KEY': 'Anthropic', 
        'GOOGLE_API_KEY': 'Google Genai'
    }
    
    available_keys = []
    for key, name in api_keys.items():
        if os.getenv(key):
            available_keys.append(name)
            print(f"✅ {name} API key found")
        else:
            print(f"⚠️  {name} API key not found")
    
    if not available_keys:
        print("ℹ️  No API keys found - skipping real API tests")
        print("   Set environment variables to test real API calls:")
        for key in api_keys.keys():
            print(f"   export {key}='your-key-here'")
        return True
    
    # Create a simple test script for real API calls
    test_script = '''
import asyncio
import os
from alpha_evolve.llm_interface import LLMInterface

async def test_real_calls():
    """Test real API calls with available keys."""
    interface = LLMInterface()
    
    # Test available providers
    if os.getenv('OPENAI_API_KEY'):
        try:
            interface.register_provider('openai', 'gpt-4o-mini')  # Use cheaper model
            result = await interface.generate_code_modification(
                "def hello(): pass",
                "Add a simple return statement",
                provider='openai'
            )
            print(f"✅ OpenAI test successful: {len(result.content)} chars, ${result.cost:.4f}")
        except Exception as e:
            print(f"❌ OpenAI test failed: {e}")
    
    if os.getenv('ANTHROPIC_API_KEY'):
        try:
            interface.register_provider('anthropic', 'claude-3-5-sonnet-v2')
            result = await interface.generate_code_modification(
                "def greet(): pass", 
                "Add a simple greeting",
                provider='anthropic'
            )
            print(f"✅ Anthropic test successful: {len(result.content)} chars, ${result.cost:.4f}")
        except Exception as e:
            print(f"❌ Anthropic test failed: {e}")
    
    if os.getenv('GOOGLE_API_KEY'):
        try:
            interface.register_provider('gemini', 'gemini-2.5-flash')
            result = await interface.generate_code_modification(
                "def calculate(): pass",
                "Add a simple calculation", 
                provider='gemini'
            )
            print(f"✅ Google test successful: {len(result.content)} chars, ${result.cost:.4f}")
        except Exception as e:
            print(f"❌ Google test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_real_calls())
'''
    
    # Write and run the test script
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_script = f.name
    
    try:
        run_command(f"python {temp_script}", capture_output=False, check=False)
    finally:
        os.unlink(temp_script)
    
    return True


def main():
    """Main test execution."""
    print("🚀 AlphaEvolve SDK Integration Testing")
    print("=" * 50)
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    print(f"Working directory: {os.getcwd()}")
    
    # Step 1: Install SDK packages
    if not install_sdk_packages():
        print("❌ Failed to install SDK packages")
        return False
    
    # Step 2: Verify imports
    if not verify_imports():
        print("❌ Failed to import SDK packages")
        return False
    
    # Step 3: Run tests
    if not run_sdk_tests():
        print("❌ SDK tests failed") 
        return False
    
    # Step 4: Test real API calls (optional)
    test_real_api_calls()
    
    print("\n🎉 SDK integration testing completed!")
    print("\nNext steps:")
    print("1. Set API keys for real testing: export OPENAI_API_KEY='...'")
    print("2. Run specific tests: pytest tests/test_sdk_integration.py -v")
    print("3. All LLM interface tests should now pass without skips")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)