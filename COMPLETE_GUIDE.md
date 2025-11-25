# Lalal AI Voice Cleaner - Complete Application

A comprehensive Python desktop application that integrates with the Lalal AI API to automatically clean voice recordings from background music and noise.

## 🎯 Features

### ✅ Core Functionality
- **Automatic Voice Cleanup**: Processes audio files to isolate and enhance voice quality
- **Folder Monitoring**: Watches input folder for new files and processes them automatically
- **Batch Processing**: Handles multiple files sequentially with progress tracking
- **Voice-Specific Processing**: Uses Lalal AI's voice cleanup feature for optimal results

### 🔐 Security & Authentication
- **Secure Credential Storage**: License key encrypted using Fernet (AES-128)
- **OAuth Authentication**: Secure API authentication flow
- **Configuration Encryption**: Sensitive data stored with encryption

### 📁 File Management
- **Configurable Folders**: Custom input/output folder paths
- **Processed File Organization**: Original files moved to processed subfolder
- **Multiple Audio Formats**: Supports MP3, WAV, FLAC, M4A, OGG, and more
- **Large File Support**: Handles files up to 10GB with valid license

### 🖥️ User Interface
- **Clean Desktop GUI**: Modern tkinter-based interface
- **Real-time Status Updates**: Live processing status and progress indicators
- **Authentication Status**: Visual indicator of API connection
- **Start/Stop Controls**: Easy control of folder watching functionality

### 📝 Logging & Monitoring
- **Comprehensive Logging**: Detailed activity logs with timestamps
- **Log Export**: Export logs to text files for analysis
- **Error Tracking**: Detailed error messages and troubleshooting info
- **Processing Statistics**: Success rates and performance metrics

### ⚡ Performance & Reliability
- **Sequential Processing**: Optimized for handling multiple files
- **Progress Indicators**: Visual feedback for long-running processes
- **Resource Cleanup**: Proper cleanup after processing completion
- **Error Recovery**: Robust error handling and recovery mechanisms

## 🚀 Quick Start

### 1. Installation
```bash
# Clone or download the application
cd lalalai_voice_cleaner

# Run the setup script
python setup.py

# Or install dependencies manually
pip install requests cryptography watchdog python-dateutil
```

### 2. Get Lalal AI License
1. Visit [Lalal AI API](https://www.lalal.ai/api/)
2. Sign up and obtain your license key
3. Note: You'll need this for authentication

### 3. Run the Application
```bash
# Windows
python main.py
# Or double-click run.bat

# Mac/Linux
python3 main.py
# Or run ./run.sh
```

### 4. Configure and Use
1. **Authenticate**: Enter your Lalal AI license key
2. **Set Folders**: Configure input and output folders
3. **Start Watching**: Click "Start Watching" to begin monitoring
4. **Process Files**: Drop audio files in the input folder
5. **Get Results**: Clean voice files appear in output folder

## 📋 Application Workflow

```
Audio File Input → Folder Watcher → File Processor → Lalal AI API → Clean Voice Output
     ↓                    ↓              ↓              ↓              ↓
   Input Folder      Detection &      Upload &     Voice Cleanup   Output Folder
   (User drops)      Queueing         Processing     Processing     (Clean files)
```

## 🔧 Configuration

### Folder Structure
```
lalalai_voice_cleaner/
├── main.py              # Main application
├── api_client.py        # Lalal AI API client
├── config_manager.py    # Configuration & encryption
├── folder_watcher.py    # File system monitoring
├── file_processor.py    # Audio file processing
├── setup.py             # Installation script
├── requirements.txt     # Dependencies
├── in/                  # Input folder (configurable)
├── out/                 # Output folder (configurable)
│   └── processed_originals/  # Original files after processing
├── logs/                # Application logs
└── test_audio/          # Sample audio files
```

### Settings
- **Input Folder**: Where you drop audio files for processing
- **Output Folder**: Where clean voice files are saved
- **Auto-start**: Option to start watching on application launch
- **Processed Folder**: Move originals to subfolder after processing

## 🛠️ Technical Details

### Architecture
- **Frontend**: tkinter-based desktop GUI
- **Backend**: Python with threading for async processing
- **API Integration**: RESTful API client for Lalal AI
- **File Monitoring**: watchdog library for folder watching
- **Security**: cryptography library for encryption

### API Integration
The application uses the Lalal AI API endpoints:
- `/api/upload/` - File upload
- `/api/split/` - Voice cleanup processing
- `/api/preview/` - Processed file retrieval

### Processing Pipeline
1. **File Detection**: Monitor input folder for new audio files
2. **File Validation**: Check format and size constraints
3. **Upload**: Send file to Lalal AI servers
4. **Processing**: Apply voice cleanup algorithms
5. **Download**: Retrieve processed clean voice file
6. **Organization**: Move original to processed folder

## 📊 Supported Audio Formats

- **MP3** (.mp3)
- **WAV** (.wav)
- **FLAC** (.flac)
- **M4A** (.m4a)
- **OGG** (.ogg)
- **WMA** (.wma)
- **AAC** (.aac)
- **AIFF** (.aiff)
- **AU** (.au)
- **RA** (.ra)
- **RAM** (.ram)

## 🔒 Security Features

### Credential Protection
- **AES-128 Encryption**: License keys encrypted with Fernet
- **Secure Storage**: Configuration files with restricted permissions
- **No Hardcoded Secrets**: All sensitive data user-provided

### Data Privacy
- **Local Processing**: Files processed locally before API upload
- **Secure API Communication**: HTTPS encrypted connections
- **No Data Retention**: Application doesn't store user audio files

## 🐛 Error Handling

### Common Issues & Solutions

#### Authentication Errors
- **Invalid License**: Check license key validity
- **Network Issues**: Verify internet connectivity
- **API Limits**: Check Lalal AI account status

#### File Processing Errors
- **Unsupported Format**: Convert to supported format
- **File Too Large**: Split large files or upgrade license
- **Corrupt Files**: Verify audio file integrity

#### Folder Watching Issues
- **Permission Denied**: Check folder read/write permissions
- **Folder Not Found**: Verify folder paths exist
- **Disk Space**: Ensure adequate storage space

## 📈 Performance Optimization

### Processing Efficiency
- **Sequential Processing**: Prevents API rate limiting
- **File Stability Checking**: Ensures files are fully written
- **Queue Management**: Efficient task scheduling
- **Resource Cleanup**: Memory and file handle management

### User Experience
- **Responsive UI**: Non-blocking processing with threading
- **Progress Feedback**: Real-time status updates
- **Error Recovery**: Graceful handling of failures
- **Logging**: Comprehensive troubleshooting information

## 🧪 Testing

Run the test suite:
```bash
python test_components.py
```

Tests cover:
- Configuration management and encryption
- API client functionality
- Folder watching capabilities
- File processing logic
- UI component initialization

## 📚 Additional Resources

### Documentation
- [Lalal AI API Documentation](https://www.lalal.ai/api/help/)
- [API Examples](https://github.com/OmniSaleGmbH/lalalai/tree/master/tools/api)

### Support
- Check logs in `lalalai_voice_cleaner.log`
- Export logs for troubleshooting
- Verify API connectivity and credentials

## 📄 License

This project is provided as-is for educational and personal use. Please respect Lalal AI's terms of service and API usage policies.

## 🤝 Contributing

Feel free to:
- Report bugs and issues
- Suggest improvements
- Submit pull requests
- Share usage examples

---

**Enjoy clean, professional voice recordings with automated background removal!** 🎤✨