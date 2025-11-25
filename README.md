# Lalal AI Voice Cleaner

A Python desktop application that integrates with the Lalal AI API to automatically clean voice recordings from background music and noise.

## Features

- **Automatic Voice Cleanup**: Processes audio files to remove background music and enhance voice quality
- **Folder Monitoring**: Watches input folder for new files and processes them automatically
- **Secure Authentication**: Implements secure OAuth authentication with credential encryption
- **Comprehensive Logging**: Tracks all processing activities with export capabilities
- **User-Friendly Interface**: Clean, responsive GUI with real-time status updates

## Requirements

- Python 3.8+
- Lalal AI API license key
- Windows/macOS/Linux

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

Or use the launcher:
```bash
python launcher.py
```

## Usage

1. **First Run**: The application will prompt for your Lalal AI license key
2. **Configure Folders**: Set up input and output folders through the settings
3. **Start Processing**: Click "Start" to begin monitoring the input folder
4. **Monitor Progress**: View real-time logs and processing status

## Supported Audio Formats

- MP3, WAV, FLAC, M4A, OGG
- Maximum file size: 10GB (with valid license)

## Project Structure

- `main.py` - Main application entry point with GUI
- `api_client.py` - Lalal AI API integration
- `config_manager.py` - Configuration management with encryption
- `file_processor.py` - File processing logic
- `folder_watcher.py` - Folder monitoring functionality
- `launcher.py` - Application launcher with mode selection
- `setup.py` - Installation and setup script
- `validate_license.py` - License validation utility

## License

This project requires a valid Lalal AI license key for API access.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions, please check the application logs and ensure your license key is valid.