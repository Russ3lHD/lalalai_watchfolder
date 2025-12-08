# Lalal AI Voice Cleaner & Converter - Complete Application Guide

A comprehensive Python desktop application that integrates with the Lalal AI API to automatically process audio files in two powerful modes: voice cleanup (background music/noise removal) and voice conversion (AI voice transformation).

## 🎯 Features

### ✅ Dual Processing Modes
- **Voice Cleanup**: Removes background music and noise, extracts specific audio stems (voice, drums, bass, piano, guitar, synthesizer, strings, wind instruments)
- **Voice Conversion**: Transforms voices using AI voice packs with advanced controls for accent enhancement and pitch shifting
- **Batch Processing**: Handles multiple files sequentially with intelligent queue management
- **Real-time Monitoring**: Live processing status, queue management, and progress tracking

### 🎛️ Advanced AI Controls
- **Neural Network Selection**: Choose from auto, phoenix, orion, or perseus AI models
- **Stem Extraction**: Extract vocals, drums, bass, piano, electric guitar, acoustic guitar, synthesizer, strings, or wind instruments
- **Processing Intensity**: Configurable noise cancelling levels (mild/normal/aggressive)
- **Dereverb Options**: Remove echo and reverb for both cleanup and conversion modes
- **Filter Control**: Post-processing filter intensity adjustment
- **Enhanced Processing**: Advanced AI processing for superior results

### 🔐 Security & Authentication
- **AES-128 Encryption**: License key encrypted using Fernet (AES-128) cryptography
- **Secure Configuration Storage**: All sensitive data encrypted with unique keys
- **API Authentication**: Secure license key-based authentication with Lalal AI
- **Protected File Permissions**: Configuration files with restricted system permissions

### 📁 File Management
- **Configurable Folders**: Custom input/output folder paths with validation
- **Intelligent Organization**: Original files automatically moved to timestamped processed subfolder
- **Multiple Audio Formats**: Supports MP3, WAV, FLAC, M4A, OGG, WMA, AAC, AIFF, AU, RA, RAM
- **Large File Support**: Handles files up to 10GB with valid Lalal AI license
- **Queue Management**: Sequential processing prevents API rate limiting
- **File Stability Checking**: Ensures files are completely written before processing

### 🖥️ User Interface
- **Modern Desktop GUI**: Clean tkinter-based interface with responsive design
- **Real-time Status Updates**: Live processing status, queue size, and progress indicators
- **Authentication Monitoring**: Visual connection status and license validation
- **Comprehensive Settings**: Detailed configuration dialog with all processing options
- **Statistics Dashboard**: Processing success rates, average times, and file counters
- **Log Management**: Built-in log viewer with export functionality

### 📝 Logging & Monitoring
- **Comprehensive Activity Logs**: Detailed timestamps, processing steps, and status updates
- **Log Export Functionality**: Export logs to text files with custom naming and timestamps
- **Advanced Error Tracking**: Detailed error messages with context and troubleshooting hints
- **Processing Statistics**: Real-time success rates, average processing times, queue status
- **Multi-level Logging**: INFO, WARNING, and ERROR levels with different detail granularity
- **UI Log Integration**: Real-time log display within the application interface

### ⚡ Performance & Reliability
- **Intelligent Queue Management**: Sequential processing prevents API rate limiting and optimizes throughput
- **Progress Tracking**: Visual feedback for upload, processing, and download phases
- **Resource Management**: Proper cleanup of memory, file handles, and network connections
- **Error Recovery**: Robust error handling with automatic retry mechanisms and graceful degradation
- **Timeout Protection**: Configurable timeouts for long-running operations
- **File Validation**: Pre-processing validation of file formats, sizes, and integrity

## 🚀 Quick Start

### 1. Installation & Setup
```bash
# Navigate to project directory
cd lalalai_watchfolder

# Install dependencies
pip install -r requirements.txt

# Optional: Run setup script for environment preparation
python setup.py

# Test installation
python test_components.py
```

### 2. Get Lalal AI License Key
1. Visit [Lalal AI API](https://www.lalal.ai/api/)
2. Sign up and obtain your API license key
3. **Important**: You'll need this license key for authentication

### 3. Launch Application
```bash
# Method 1: Direct launch (recommended for first-time users)
python main.py

# Method 2: Use launcher for mode selection
python launcher.py

# Method 3: Platform-specific scripts
# Windows: Double-click run.bat
# Mac/Linux: ./run.sh
```

### 4. Initial Configuration
1. **Authentication**: Enter your Lalal AI license key when prompted
2. **Folder Setup**: Configure input and output folder paths using "Browse" buttons
3. **Processing Mode**: Choose between "voice_cleanup" or "voice_converter" in Settings
4. **Advanced Settings**: Customize AI models, processing options, and voice packs

### 5. Start Processing
1. **Start Monitoring**: Click "Start Watching" to begin folder monitoring
2. **Add Files**: Drop audio files into your configured input folder
3. **Monitor Progress**: Watch real-time processing status and logs
4. **Retrieve Results**: Find processed files in your output folder

### 6. Processing Modes Explained

#### Voice Cleanup Mode
- **Purpose**: Remove background music/noise from recordings
- **Best For**: Podcasts, interviews, voice memos with background noise
- **Key Settings**: Stem selection (voice/drums/bass/etc.), noise cancelling level, dereverb
- **Output**: Files named `cleaned_[original_filename]`

#### Voice Conversion Mode  
- **Purpose**: Transform voice using AI voice packs
- **Best For**: Voice acting, character voices, voice enhancement
- **Key Settings**: Voice pack selection (ALEX_KAYE, JENNIFER, etc.), accent enhancement, pitch shifting
- **Output**: Files named `converted_[original_filename]`

## 📋 Application Workflow

### Voice Cleanup Processing Pipeline
```
Audio File → File Validation → Upload to API → AI Processing → Download Result → File Organization
     ↓              ↓               ↓               ↓               ↓               ↓
Input Folder   Format/Size     Queue & Upload   Voice Cleanup   Output Folder   Processed Folder
(User drops)   Check           Management       & Stem Extract   (Clean files)   (Originals)
```

### Voice Conversion Processing Pipeline  
```
Audio File → File Validation → Upload to API → AI Voice Conversion → Download Result → File Organization
     ↓              ↓               ↓                   ↓                    ↓               ↓
Input Folder   Format/Size     Queue & Upload   Voice Pack Transform   Output Folder   Processed Folder
(User drops)   Check           Management       (Accent/Pitch/Dereverb)  (Converted)    (Originals)
```

### Processing Steps Detail
1. **File Detection**: Watchdog monitors input folder for new audio files
2. **File Validation**: Check format support, file size (max 10GB), and file integrity
3. **Queue Management**: Add files to processing queue with status tracking
4. **API Upload**: Upload file to Lalal AI servers with progress monitoring
5. **AI Processing**: Apply selected AI model (cleanup or conversion) with configured parameters
6. **Result Download**: Download processed file with progress tracking
7. **File Organization**: Move original to processed subfolder, save result to output folder

## 🔧 Configuration

### Project Structure
```
lalalai_watchfolder/
├── main.py                  # Main desktop application (API mode)
├── launcher.py              # Application launcher with mode selection
├── api_client.py            # Lalal AI API integration client
├── config_manager.py        # Configuration management with AES encryption
├── file_processor.py        # Audio file processing logic
├── folder_watcher.py        # Folder monitoring functionality
├── test_components.py       # Comprehensive component testing suite
├── validate_license.py      # License validation utility
├── setup.py                 # Installation and setup script
├── requirements.txt         # Python dependencies
├── run.bat                  # Windows launch script
├── run.sh                   # Unix/Linux launch script
├── README.md               # Project overview
├── COMPLETE_GUIDE.md       # This comprehensive guide
├── logs/                   # Application logs directory
│   └── lalalai_voice_cleaner.log
└── test_audio/             # Sample audio files for testing
```

### Configuration Management
- **Encrypted Storage**: Configuration stored in `~/.lalalai_voice_cleaner/config.json`
- **Encryption Key**: Stored in `~/.lalalai_voice_cleaner/.key` (AES-128 Fernet)
- **Auto-save**: Settings automatically saved when changed
- **Secure Permissions**: Configuration files with restricted system access (0o600)

### Settings Categories

#### Processing Mode
- **Voice Cleanup**: Background removal and stem extraction
- **Voice Converter**: AI voice transformation

#### Voice Cleanup Settings
- **Enhanced Processing**: Advanced AI processing (default: enabled)
- **Noise Cancelling Level**: Mild (0), Normal (1), Aggressive (2)
- **Dereverb**: Remove echo and reverb (default: enabled)
- **Stem Selection**: voice, vocals, drum, bass, piano, electric_guitar, acoustic_guitar, synthesizer, strings, wind
- **Neural Network**: auto, phoenix, orion, perseus
- **Filter Intensity**: Mild (0), Normal (1), Aggressive (2)

#### Voice Converter Settings
- **Voice Pack**: ALEX_KAYE, JENNIFER, DAVID, SARAH, MICHAEL
- **Accent Enhance**: 0.5 to 2.0 scale (default: 1.0)
- **Pitch Shifting**: Enable/disable (default: enabled)
- **Dereverb**: Enable/disable for voice conversion (default: disabled)

#### General Settings
- **Input Folder**: Directory to monitor for new audio files
- **Output Folder**: Directory for processed results
- **Auto-start**: Start folder watching on application launch
- **Create Processed Folder**: Move originals to timestamped subfolder

## 🛠️ Technical Details

### Architecture Overview
- **Frontend**: tkinter-based desktop GUI with custom styling and responsive design
- **Backend**: Python with multi-threading for non-blocking async processing
- **API Integration**: Comprehensive RESTful API client with session management
- **File Monitoring**: watchdog library for real-time folder monitoring
- **Security**: cryptography library with Fernet AES-128 encryption
- **Queue Management**: Thread-safe queue system for processing coordination

### Core Components

#### API Client (`api_client.py`)
- **Session Management**: Persistent HTTP session with authentication headers
- **File Upload**: Streaming upload with progress tracking and timeout handling
- **Voice Cleanup**: `/split/` endpoint with comprehensive parameter support
- **Voice Conversion**: `/voice_convert/` endpoint with voice pack integration
- **Job Monitoring**: Status checking with configurable polling intervals
- **Download Management**: Streamed download with chunk processing

#### File Processor (`file_processor.py`)
- **Queue Management**: Thread-safe processing queue with statistics tracking
- **Format Validation**: Pre-processing format and size verification
- **Dual Mode Support**: Voice cleanup and voice conversion processing
- **Error Handling**: Comprehensive exception handling with retry logic
- **Statistics Tracking**: Processing success rates, timing, and performance metrics

#### Configuration Manager (`config_manager.py`)
- **Encryption**: AES-128 Fernet encryption for sensitive data
- **Key Management**: Automatic encryption key generation and rotation
- **Secure Storage**: Protected file permissions (0o600) for configuration files
- **Data Protection**: Base64 encoding for encrypted configuration values

#### Folder Watcher (`folder_watcher.py`)
- **Real-time Monitoring**: Watchdog-based file system monitoring
- **File Stability**: Ensures complete file writes before processing
- **Event Filtering**: Filters for supported audio formats only
- **Background Processing**: Daemon thread for non-blocking monitoring

### API Integration Details

#### Authentication
```
Authorization: license YOUR_LICENSE_KEY
User-Agent: LalalAIVoiceCleaner/1.0.0
```

#### Endpoint Usage
- **File Upload**: `POST https://www.lalal.ai/api/upload/`
- **Voice Cleanup**: `POST https://www.lalal.ai/api/split/`
- **Voice Conversion**: `POST https://www.lalal.ai/api/voice_convert/`
- **Voice Packs**: `GET https://www.lalal.ai/api/voice_packs/list/`

#### Processing Parameters
**Voice Cleanup:**
```json
{
  "id": "file_id",
  "stem": "voice|drum|bass|piano|guitar|synthesizer|strings|wind",
  "splitter": "auto|phoenix|orion|perseus",
  "filter": 0|1|2,
  "enhanced_processing_enabled": true|false,
  "noise_cancelling_level": 0|1|2,
  "dereverb_enabled": true|false
}
```

**Voice Conversion:**
```json
{
  "id": "file_id",
  "voice_pack_id": "ALEX_KAYE|JENNIFER|DAVID|SARAH|MICHAEL",
  "accent_enhance": 0.5-2.0,
  "pitch_shifting": true|false,
  "dereverb_enabled": true|false
}
```

## 📊 Supported Audio Formats & Specifications

### Input Formats
- **MP3** (.mp3) - Most common compressed format
- **WAV** (.wav) - Uncompressed PCM audio
- **FLAC** (.flac) - Lossless compression
- **M4A** (.m4a) - Apple AAC format
- **OGG** (.ogg) - Open-source compressed format
- **WMA** (.wma) - Windows Media Audio
- **AAC** (.aac) - Advanced Audio Coding
- **AIFF** (.aiff) - Audio Interchange File Format
- **AU** (.au) - Sun Microsystems audio format
- **RA** (.ra) - Real Audio format
- **RAM** (.ram) - Real Audio Meta file

### File Specifications
- **Maximum File Size**: 10GB (requires valid Lalal AI license)
- **Recommended Duration**: Up to 30 minutes per file for optimal processing
- **Sample Rate**: All standard sample rates supported (44.1kHz, 48kHz, 96kHz, etc.)
- **Bit Depth**: 8-bit, 16-bit, 24-bit, 32-bit float supported
- **Channels**: Mono, stereo, and multi-channel audio supported

### Output Specifications
- **Output Naming**: 
  - Voice Cleanup: `cleaned_[original_filename]`
  - Voice Conversion: `converted_[original_filename]`
- **Output Format**: Same format as input (when possible)
- **Quality**: Maintains original audio quality with AI processing applied
- **Organization**: Original files moved to `processed_originals/` subfolder with timestamps

## 🔒 Security Features

### Credential Protection
- **AES-128 Encryption**: License keys encrypted with Fernet
- **Secure Storage**: Configuration files with restricted permissions
- **No Hardcoded Secrets**: All sensitive data user-provided

### Data Privacy
- **Local Processing**: Files processed locally before API upload
- **Secure API Communication**: HTTPS encrypted connections
- **No Data Retention**: Application doesn't store user audio files

## 📦 Dependencies

### Required Packages
```
requests==2.31.0        # HTTP library for API communication
cryptography==41.0.7    # Encryption for secure credential storage
watchdog==3.0.0         # File system monitoring
tkinter-tooltip==2.1.0  # Enhanced GUI tooltips
pillow==10.1.0          # Image processing for GUI
python-dateutil==2.8.2  # Date/time utilities
```

### Installation
```bash
pip install -r requirements.txt
```

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+)
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 1GB free space for application and logs
- **Network**: Stable internet connection for API communication

## 🐛 Error Handling & Troubleshooting

### Common Issues & Solutions

#### Authentication & License Errors
- **Invalid License Key**: 
  - Verify license key at [lalal.ai/api](https://www.lalal.ai/api/)
  - Check license expiration status
  - Ensure license has API access enabled
- **Authentication Failed**: 
  - Verify internet connection
  - Check firewall/proxy settings
  - Confirm Lalal AI service status
- **API Rate Limiting**: 
  - Reduce processing frequency
  - Check account limits and quotas
  - Upgrade license if needed

#### File Processing Errors
- **Unsupported Format**: 
  - Convert to supported format using audio software
  - Check file extension matches actual format
  - Verify file isn't corrupted
- **File Too Large (>10GB)**:
  - Split large files into smaller segments
  - Consider upgrading to higher license tier
  - Compress file if possible
- **Corrupt Audio Files**:
  - Test file with audio playback software
  - Re-encode from original source
  - Check file isn't partially downloaded
- **Processing Timeout**:
  - Check internet connection stability
  - Try smaller file sizes
  - Increase timeout settings in configuration

#### Folder Watching Issues
- **Permission Denied**:
  - Check folder read/write permissions
  - Run application as administrator (Windows)
  - Verify antivirus isn't blocking access
- **Folder Not Found**:
  - Verify folder paths exist and are accessible
  - Check for typos in folder names
  - Use "Browse" buttons to select folders
- **Disk Space Issues**:
  - Ensure adequate free space (minimum 2x file size)
  - Clean up old processed files
  - Monitor output folder size

#### Network & API Issues
- **Connection Timeout**:
  - Check internet connection
  - Verify firewall settings
  - Try different network if available
- **API Service Unavailable**:
  - Check Lalal AI service status
  - Wait for service restoration
  - Monitor API status page
- **Upload Failures**:
  - Check file integrity
  - Verify sufficient upload bandwidth
  - Try uploading smaller files first

### Debug Information
- **Log Files**: Check `lalalai_voice_cleaner.log` for detailed error information
- **Export Logs**: Use "Export Logs" button in application for troubleshooting
- **Test Components**: Run `python test_components.py` to verify installation
- **Network Test**: Use `python validate_license.py YOUR_KEY` to test API connectivity

### Performance Optimization
- **Slow Processing**: 
  - Check internet connection speed
  - Try processing smaller files first
  - Monitor system resource usage
- **High Memory Usage**:
  - Process files individually instead of batch
  - Close other applications
  - Monitor RAM usage during processing

## 📈 Performance Optimization

### Processing Efficiency
- **Sequential Processing**: Prevents API rate limiting and optimizes throughput
- **File Stability Checking**: Ensures complete file writes before processing
- **Intelligent Queue Management**: Efficient task scheduling with priority handling
- **Resource Cleanup**: Proper memory and file handle management
- **Timeout Protection**: Configurable timeouts prevent hanging operations

### User Experience Optimization
- **Responsive UI**: Non-blocking processing with dedicated worker threads
- **Real-time Feedback**: Live status updates, progress indicators, and queue monitoring
- **Graceful Error Recovery**: Automatic retry mechanisms and user-friendly error messages
- **Comprehensive Logging**: Detailed troubleshooting information with export capabilities
- **Statistics Dashboard**: Real-time performance metrics and success tracking

### Best Practices
- **File Size Management**: Process files under 100MB for optimal performance
- **Network Quality**: Use stable internet connection for consistent processing
- **System Resources**: Close unnecessary applications during batch processing
- **Folder Organization**: Use descriptive input/output folder names for easy management

## 🧪 Testing & Validation

### Component Testing
Run the comprehensive test suite:
```bash
python test_components.py
```

### Test Coverage
- **Configuration Management**: Encryption/decryption functionality
- **API Client**: Connection testing and request handling
- **Folder Watching**: File detection and monitoring capabilities
- **File Processing**: Upload, processing, and download workflows
- **UI Components**: Interface initialization and responsiveness
- **Error Handling**: Exception management and recovery

### Validation Tools
```bash
# License validation
python validate_license.py YOUR_LICENSE_KEY

# Setup verification
python setup.py

# Individual component tests
python -m pytest test_components.py  # If pytest is available
```

## 📚 Additional Resources

### Official Documentation
- [Lalal AI API Documentation](https://www.lalal.ai/api/help/) - Comprehensive API reference
- [Lalal AI Website](https://www.lalal.ai/) - Service status and updates
- [API Examples Repository](https://github.com/OmniSaleGmbH/lalalai/tree/master/tools/api) - Code examples

### Community Resources
- **GitHub Issues**: Report bugs and request features
- **Discussion Forums**: Community support and tips
- **Video Tutorials**: Step-by-step usage guides
- **Blog Posts**: Advanced usage scenarios and tips

### Support Channels
- **Application Logs**: Check `lalalai_voice_cleaner.log` for detailed information
- **Export Logs**: Use built-in export functionality for troubleshooting
- **Diagnostic Mode**: Enable verbose logging in settings for detailed debugging
- **System Information**: Include OS, Python version, and error details when reporting issues

## 📄 License & Legal

This project is provided as-is for educational and personal use. 

### Important Notes
- **Lalal AI API**: Requires valid license key for access
- **Terms of Service**: Respect Lalal AI's API usage policies and rate limits
- **Data Privacy**: Audio files are processed through third-party servers
- **Commercial Use**: Check Lalal AI licensing terms for commercial applications

### Disclaimer
This application is not officially affiliated with Lalal AI. It is an independent tool that integrates with their public API.

## 🤝 Contributing

We welcome contributions from the community! Here's how you can help:

### Ways to Contribute
- **Bug Reports**: Submit detailed issue reports with logs and reproduction steps
- **Feature Requests**: Suggest new functionality and improvements
- **Code Contributions**: Submit pull requests with bug fixes or new features
- **Documentation**: Improve guides, add examples, fix typos
- **Testing**: Test on different platforms and report compatibility issues

### Development Guidelines
1. **Fork the Repository**: Create your own fork for development
2. **Create Feature Branch**: Use descriptive branch names (`feature/voice-conversion-ui`)
3. **Write Tests**: Add tests for new functionality
4. **Follow Code Style**: Maintain consistent coding standards
5. **Update Documentation**: Keep docs synchronized with code changes
6. **Submit Pull Request**: Include clear description and testing results

### Code Standards
- **Python Style**: Follow PEP 8 guidelines
- **Documentation**: Add docstrings for all functions and classes
- **Error Handling**: Implement comprehensive exception handling
- **Security**: Maintain encryption and security best practices
- **Performance**: Consider efficiency in all changes

---

## 🎯 Conclusion

**Lalal AI Voice Cleaner & Converter** provides a powerful, user-friendly solution for automated audio processing. Whether you need to clean voice recordings from background noise or transform voices using AI technology, this application offers professional-grade capabilities with an intuitive interface.

### Key Benefits
- **Dual Functionality**: Both cleanup and conversion in one application
- **Professional Results**: High-quality AI-powered audio processing
- **User-Friendly**: Simple setup and operation for all skill levels
- **Secure & Reliable**: Encrypted storage and robust error handling
- **Comprehensive**: Complete workflow from input to organized output

### Next Steps
1. **Install and Setup**: Follow the quick start guide to get running
2. **Explore Settings**: Customize AI models and processing options for your needs
3. **Process Files**: Start with small files to understand the workflow
4. **Optimize Performance**: Adjust settings based on your audio content and requirements
5. **Share Feedback**: Help improve the application for everyone

**Enjoy professional-grade audio processing with automated AI technology!** 🎤✨🚀

---

*Last Updated: December 2024*
*Application Version: 1.0.0*