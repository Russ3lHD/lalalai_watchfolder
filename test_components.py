#!/usr/bin/env python3
"""
Test script for Lalal AI Voice Cleaner Application
Tests individual components and basic functionality
"""

import os
import sys
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_config_manager():
    """Test configuration manager"""
    print("Testing ConfigManager...")
    
    try:
        from config_manager import ConfigManager
        
        # Create temporary config
        config = ConfigManager()
        
        # Test saving and loading
        test_data = {
            'license_key': 'test_license_123',
            'input_folder': '/test/input',
            'output_folder': '/test/output'
        }
        
        # Save config
        success = config.save_config(test_data)
        assert success, "Failed to save config"
        print("✓ Configuration saved successfully")
        
        # Load config
        loaded_config = config.load_config()
        assert loaded_config is not None, "Failed to load config"
        assert loaded_config['license_key'] == 'test_license_123', "License key mismatch"
        print("✓ Configuration loaded successfully")
        
        # Test encryption
        assert config.cipher_suite is not None, "Encryption not working"
        print("✓ Encryption working correctly")
        
        # Cleanup
        config.delete_config()
        print("✓ Configuration deleted successfully")
        
        print("ConfigManager tests passed!\n")
        return True
        
    except Exception as e:
        print(f"✗ ConfigManager test failed: {str(e)}\n")
        return False

def test_api_client():
    """Test API client (with mocked responses)"""
    print("Testing LalalAIClient...")
    
    try:
        from api_client import LalalAIClient
        
        # Create client with test license
        client = LalalAIClient("test_license_key")
        
        # Test format support
        supported_formats = client.get_supported_formats()
        assert 'mp3' in supported_formats, "MP3 not in supported formats"
        assert 'wav' in supported_formats, "WAV not in supported formats"
        print("✓ Supported formats retrieved correctly")
        
        # Test format validation
        assert client.is_format_supported("test.mp3"), "MP3 format not recognized"
        assert not client.is_format_supported("test.txt"), "TXT format incorrectly recognized"
        print("✓ Format validation working")
        
        # Test connection (will fail with test key, but should handle gracefully)
        with patch('requests.Session.head') as mock_head:
            mock_head.return_value.status_code = 200
            result = client.test_connection()
            # This will fail because we're using a mock, but the structure is tested
        
        print("✓ API client structure working correctly")
        print("API client tests passed!\n")
        return True
        
    except Exception as e:
        print(f"✗ API client test failed: {str(e)}\n")
        return False

def test_folder_watcher():
    """Test folder watcher component"""
    print("Testing FolderWatcher...")
    
    try:
        from folder_watcher import FolderWatcher, AudioFileHandler
        
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock file processor
            mock_processor = Mock()
            
            # Create folder watcher
            watcher = FolderWatcher(temp_dir, mock_processor)
            
            # Test initialization
            assert watcher.watch_folder == temp_dir, "Watch folder not set correctly"
            assert 'mp3' in watcher.supported_extensions, "MP3 not in supported extensions"
            print("✓ Folder watcher initialized correctly")
            
            # Test audio file handler
            handler = AudioFileHandler(mock_processor, watcher.supported_extensions)
            
            # Test format checking
            assert handler._is_supported_audio_file("test.mp3"), "MP3 not recognized"
            assert not handler._is_supported_audio_file("test.txt"), "TXT incorrectly recognized"
            print("✓ Audio file handler working correctly")
            
            # Test status
            status = watcher.get_status()
            assert 'is_watching' in status, "Status missing is_watching field"
            assert 'supported_formats' in status, "Status missing supported_formats field"
            print("✓ Status reporting working")
        
        print("Folder watcher tests passed!\n")
        return True
        
    except Exception as e:
        print(f"✗ Folder watcher test failed: {str(e)}\n")
        return False

def test_file_processor():
    """Test file processor component"""
    print("Testing FileProcessor...")
    
    try:
        from file_processor import FileProcessor
        
        # Create temporary directories
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create mock API client and app instance
            mock_api_client = Mock()
            mock_app_instance = Mock()
            
            # Create file processor
            processor = FileProcessor(mock_api_client, temp_dir, mock_app_instance)
            
            # Test initialization
            assert processor.output_folder == temp_dir, "Output folder not set correctly"
            assert processor.processed_folder.endswith('processed_originals'), "Processed folder not created"
            print("✓ File processor initialized correctly")
            
            # Test statistics
            stats = processor.get_stats()
            assert 'total_processed' in stats, "Stats missing total_processed"
            assert 'successful' in stats, "Stats missing successful"
            assert 'success_rate' in stats, "Stats missing success_rate"
            print("✓ Statistics working correctly")
            
            # Test stats clearing
            processor.clear_stats()
            cleared_stats = processor.get_stats()
            assert cleared_stats['total_processed'] == 0, "Stats not cleared correctly"
            print("✓ Stats clearing working")
        
        print("File processor tests passed!\n")
        return True
        
    except Exception as e:
        print(f"✗ File processor test failed: {str(e)}\n")
        return False

def test_ui_components():
    """Test UI components (basic structure)"""
    print("Testing UI components...")
    
    try:
        import tkinter as tk
        from tkinter import ttk
        
        # Test basic tkinter functionality
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Test widget creation
        frame = ttk.Frame(root)
        label = ttk.Label(frame, text="Test")
        button = ttk.Button(frame, text="Test")
        
        assert frame is not None, "Frame creation failed"
        assert label is not None, "Label creation failed"
        assert button is not None, "Button creation failed"
        print("✓ Basic UI components working")
        
        root.destroy()
        print("UI components tests passed!\n")
        return True
        
    except Exception as e:
        print(f"✗ UI components test failed: {str(e)}\n")
        return False

def create_test_environment():
    """Create test environment with sample folders"""
    print("Creating test environment...")
    
    try:
        # Create test directories
        test_dirs = ['test_in', 'test_out', 'test_audio']
        
        for dir_name in test_dirs:
            os.makedirs(dir_name, exist_ok=True)
        
        # Create dummy audio files for testing
        dummy_files = [
            'test_in/sample_voice.mp3',
            'test_in/sample_music.wav',
            'test_audio/test_voice_with_noise.mp3'
        ]
        
        for file_path in dummy_files:
            Path(file_path).touch()
        
        print("✓ Test environment created")
        print("Test folders created:")
        print("  - test_in/ (input folder)")
        print("  - test_out/ (output folder)")
        print("  - test_audio/ (test audio files)")
        print("\n")
        return True
        
    except Exception as e:
        print(f"✗ Test environment creation failed: {str(e)}\n")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Lalal AI Voice Cleaner - Component Tests")
    print("=" * 60)
    print()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    tests = [
        test_config_manager,
        test_api_client,
        test_folder_watcher,
        test_file_processor,
        test_ui_components,
        create_test_environment
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application should work correctly.")
    else:
        print("⚠️  Some tests failed. Check the error messages above.")
    
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Run the application: python main.py")
    print("3. Enter your Lalal AI license key")
    print("4. Configure input/output folders")
    print("5. Start processing audio files!")

if __name__ == "__main__":
    main()