#!/usr/bin/env python3
"""
Setup script for Lalal AI Voice Cleaner Application
Automates the installation and initial configuration
"""

import os
import sys
import subprocess
import logging
from pathlib import Path

def install_dependencies():
    """Install required Python packages"""
    print("Installing dependencies...")
    
    # Core dependencies that work reliably
    core_packages = [
        'requests>=2.31.0',
        'cryptography>=41.0.0',
        'watchdog>=3.0.0',
        'python-dateutil>=2.8.0'
    ]
    
    try:
        # Install core packages
        for package in core_packages:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
        
        print("✓ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {str(e)}")
        return False

def create_directories():
    """Create necessary directories"""
    print("Creating directories...")
    
    try:
        # Create default folders
        directories = [
            'in',
            'out',
            'logs',
            'test_audio'
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
            print(f"✓ Created directory: {directory}")
        
        print("✓ Directories created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create directories: {str(e)}")
        return False

def create_sample_files():
    """Create sample files for testing"""
    print("Creating sample files...")
    
    try:
        # Create sample audio files (empty files for testing structure)
        sample_files = [
            'test_audio/sample_voice_with_music.mp3',
            'test_audio/sample_voice_with_noise.wav',
            'test_audio/sample_clean_voice.flac'
        ]
        
        for file_path in sample_files:
            Path(file_path).touch()
            print(f"✓ Created sample file: {file_path}")
        
        # Create a README for the test audio folder
        readme_content = """# Test Audio Files

This folder contains sample audio files for testing the Lalal AI Voice Cleaner application.

## Files
- `sample_voice_with_music.mp3` - Voice recording with background music
- `sample_voice_with_noise.wav` - Voice recording with background noise  
- `sample_clean_voice.flac` - Clean voice recording (for comparison)

## Usage
1. Copy these files to your input folder
2. Start the folder watcher
3. Processed files will appear in your output folder

## Note
These are placeholder files for testing the application structure.
Replace them with actual audio files for real processing.
"""
        
        with open('test_audio/README.md', 'w') as f:
            f.write(readme_content)
        
        print("✓ Sample files created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create sample files: {str(e)}")
        return False

def run_tests():
    """Run basic tests to verify installation"""
    print("Running tests...")
    
    try:
        # Import and test basic functionality
        from config_manager import ConfigManager
        from api_client import LalalAIClient
        from folder_watcher import FolderWatcher
        from file_processor import FileProcessor
        
        # Test config manager
        config = ConfigManager()
        test_config = {'test_key': 'test_value'}
        config.save_config(test_config)
        loaded_config = config.load_config()
        assert loaded_config['test_key'] == 'test_value'
        config.delete_config()
        
        # Test API client creation
        client = LalalAIClient("test_license")
        formats = client.get_supported_formats()
        assert 'mp3' in formats
        
        print("✓ Tests passed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Tests failed: {str(e)}")
        return False

def create_run_script():
    """Create a run script for easy application startup"""
    print("Creating run script...")
    
    try:
        # Create Windows batch file
        batch_content = """@echo off
echo Starting Lalal AI Voice Cleaner...
python main.py
pause
"""
        
        with open('run.bat', 'w') as f:
            f.write(batch_content)
        
        # Create Unix shell script
        shell_content = """#!/bin/bash
echo "Starting Lalal AI Voice Cleaner..."
python3 main.py
"""
        
        with open('run.sh', 'w') as f:
            f.write(shell_content)
        
        # Make shell script executable (on Unix systems)
        try:
            os.chmod('run.sh', 0o755)
        except:
            pass  # Windows doesn't support chmod in the same way
        
        print("✓ Run scripts created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Failed to create run scripts: {str(e)}")
        return False

def main():
    """Main setup function"""
    print("=" * 60)
    print("Lalal AI Voice Cleaner - Setup Script")
    print("=" * 60)
    print()
    
    # Run setup steps
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Creating directories", create_directories),
        ("Creating sample files", create_sample_files),
        ("Running tests", run_tests),
        ("Creating run scripts", create_run_script)
    ]
    
    passed = 0
    total = len(steps)
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        if step_func():
            passed += 1
        else:
            print(f"✗ {step_name} failed!")
            break
    
    print("\n" + "=" * 60)
    print(f"Setup Results: {passed}/{total} steps completed successfully")
    
    if passed == total:
        print("🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Get your Lalal AI API license from https://www.lalal.ai/api/")
        print("2. Run the application: python main.py")
        print("3. Enter your license key in the authentication section")
        print("4. Configure input/output folders")
        print("5. Start processing audio files!")
        print("\nOr use the run scripts:")
        print("- Windows: double-click run.bat")
        print("- Mac/Linux: ./run.sh")
    else:
        print("⚠️  Setup incomplete. Check the error messages above.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()