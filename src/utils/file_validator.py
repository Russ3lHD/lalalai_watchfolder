"""
File validation utilities for robust file processing
Provides comprehensive file integrity and format validation
"""

import os
import hashlib
import mimetypes
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from .exceptions import (
    FileNotFoundError, FileFormatError, FileCorruptedError, 
    FileSizeError, FileProcessingError
)


class FileValidator:
    """
    Comprehensive file validation for audio processing
    """
    
    SUPPORTED_FORMATS = {
        'mp3': {'mime_types': ['audio/mpeg', 'audio/mp3'], 'max_size': 10 * 1024 * 1024 * 1024},  # 10GB
        'wav': {'mime_types': ['audio/wav', 'audio/x-wav', 'audio/wave'], 'max_size': 10 * 1024 * 1024 * 1024},
        'flac': {'mime_types': ['audio/flac', 'audio/x-flac'], 'max_size': 10 * 1024 * 1024 * 1024},
        'm4a': {'mime_types': ['audio/mp4', 'audio/m4a'], 'max_size': 10 * 1024 * 1024 * 1024},
        'ogg': {'mime_types': ['audio/ogg', 'audio/vorbis'], 'max_size': 10 * 1024 * 1024 * 1024},
        'wma': {'mime_types': ['audio/x-ms-wma'], 'max_size': 10 * 1024 * 1024 * 1024},
        'aac': {'mime_types': ['audio/aac', 'audio/x-aac'], 'max_size': 10 * 1024 * 1024 * 1024},
        'aiff': {'mime_types': ['audio/aiff', 'audio/x-aiff'], 'max_size': 10 * 1024 * 1024 * 1024},
        'au': {'mime_types': ['audio/basic', 'audio/x-au'], 'max_size': 10 * 1024 * 1024 * 1024},
        'ra': {'mime_types': ['audio/x-pn-realaudio', 'audio/vnd.rn-realaudio'], 'max_size': 10 * 1024 * 1024 * 1024},
        'ram': {'mime_types': ['audio/x-pn-realaudio', 'audio/vnd.rn-realaudio'], 'max_size': 10 * 1024 * 1024 * 1024}
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_file(self, file_path: str, strict: bool = True) -> Dict[str, any]:
        """
        Perform comprehensive file validation
        
        Args:
            file_path: Path to the file to validate
            strict: If True, perform stricter validation checks
            
        Returns:
            Dict containing validation results
        """
        result = {
            'is_valid': True,
            'file_path': file_path,
            'errors': [],
            'warnings': [],
            'file_info': {}
        }
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(file_path)
            
            # Get file information
            file_info = self._get_file_info(file_path)
            result['file_info'] = file_info
            
            # Validate file size
            size_validation = self._validate_file_size(file_path, file_info['size'])
            if not size_validation['valid']:
                result['errors'].extend(size_validation['errors'])
            
            # Validate file format
            format_validation = self._validate_file_format(file_path, file_info)
            if not format_validation['valid']:
                result['errors'].extend(format_validation['errors'])
            
            # Validate file integrity (if strict mode)
            if strict:
                integrity_validation = self._validate_file_integrity(file_path, file_info)
                if not integrity_validation['valid']:
                    result['errors'].extend(integrity_validation['errors'])
            
            # Check file permissions
            permission_validation = self._validate_file_permissions(file_path)
            if not permission_validation['valid']:
                result['warnings'].extend(permission_validation['warnings'])
            
            # Overall validation result
            result['is_valid'] = len(result['errors']) == 0
            
            if result['is_valid']:
                self.logger.info(f"File validation passed: {file_path}")
            else:
                self.logger.warning(f"File validation failed: {file_path} - Errors: {result['errors']}")
            
            return result
            
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"Validation failed: {str(e)}")
            self.logger.error(f"File validation error for {file_path}: {str(e)}")
            return result
    
    def validate_directory(self, dir_path: str) -> Dict[str, any]:
        """
        Validate directory accessibility and permissions
        
        Args:
            dir_path: Path to the directory to validate
            
        Returns:
            Dict containing validation results
        """
        result = {
            'is_valid': True,
            'path': dir_path,
            'errors': [],
            'warnings': []
        }
        
        try:
            path_obj = Path(dir_path)
            
            # Check if directory exists
            if not path_obj.exists():
                result['is_valid'] = False
                result['errors'].append(f"Directory does not exist: {dir_path}")
                return result
            
            # Check if it's a directory
            if not path_obj.is_dir():
                result['is_valid'] = False
                result['errors'].append(f"Path is not a directory: {dir_path}")
                return result
            
            # Check read permissions
            if not os.access(dir_path, os.R_OK):
                result['is_valid'] = False
                result['errors'].append(f"No read permission for directory: {dir_path}")
            
            # Check write permissions
            if not os.access(dir_path, os.W_OK):
                result['is_valid'] = False
                result['errors'].append(f"No write permission for directory: {dir_path}")
            
            # Check execute permissions (needed to list contents)
            if not os.access(dir_path, os.X_OK):
                result['is_valid'] = False
                result['errors'].append(f"No execute permission for directory: {dir_path}")
            
            if result['is_valid']:
                self.logger.info(f"Directory validation passed: {dir_path}")
            
            return result
            
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"Directory validation error: {str(e)}")
            self.logger.error(f"Error validating directory {dir_path}: {str(e)}")
            return result
    
    def _get_file_info(self, file_path: str) -> Dict[str, any]:
        """Get detailed file information"""
        path_obj = Path(file_path)
        stat_info = path_obj.stat()
        
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Get file extension
        extension = path_obj.suffix.lower().lstrip('.')
        
        return {
            'path': str(path_obj),
            'name': path_obj.name,
            'extension': extension,
            'size': stat_info.st_size,
            'mime_type': mime_type,
            'created': stat_info.st_ctime,
            'modified': stat_info.st_mtime,
            'accessed': stat_info.st_atime,
            'is_file': path_obj.is_file(),
            'is_readable': os.access(file_path, os.R_OK),
            'is_writable': os.access(file_path, os.W_OK)
        }
    
    def _validate_file_size(self, file_path: str, file_size: int) -> Dict[str, any]:
        """Validate file size"""
        result = {'valid': True, 'errors': []}
        
        if file_size == 0:
            result['valid'] = False
            result['errors'].append("File is empty")
            return result
        
        if file_size < 0:
            result['valid'] = False
            result['errors'].append("File has negative size")
            return result
        
        # Check against format-specific limits
        extension = Path(file_path).suffix.lower().lstrip('.')
        if extension in self.SUPPORTED_FORMATS:
            max_size = self.SUPPORTED_FORMATS[extension]['max_size']
            if file_size > max_size:
                result['valid'] = False
                result['errors'].append(
                    f"File size ({file_size} bytes) exceeds maximum allowed size "
                    f"({max_size} bytes) for {extension} format"
                )
        
        return result
    
    def _validate_file_format(self, file_path: str, file_info: Dict) -> Dict[str, any]:
        """Validate file format and extension"""
        result = {'valid': True, 'errors': []}
        
        extension = file_info['extension']
        mime_type = file_info['mime_type']
        
        # Check if format is supported
        if extension not in self.SUPPORTED_FORMATS:
            result['valid'] = False
            result['errors'].append(
                f"Unsupported file format: {extension}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS.keys())}"
            )
            return result
        
        # Validate MIME type if available
        if mime_type:
            expected_mime_types = self.SUPPORTED_FORMATS[extension]['mime_types']
            if mime_type not in expected_mime_types:
                result['errors'].append(
                    f"MIME type mismatch: {mime_type} vs expected "
                    f"{expected_mime_types} for {extension} format"
                )
        
        # Additional format-specific checks
        try:
            format_specific_validation = self._validate_format_specific(file_path, extension)
            if not format_specific_validation['valid']:
                result['valid'] = False
                result['errors'].extend(format_specific_validation['errors'])
        except Exception as e:
            result['errors'].append(f"Format-specific validation failed: {str(e)}")
        
        return result
    
    def _validate_format_specific(self, file_path: str, extension: str) -> Dict[str, any]:
        """Perform format-specific validation"""
        result = {'valid': True, 'errors': []}
        
        if extension == 'mp3':
            result = self._validate_mp3_file(file_path)
        elif extension == 'wav':
            result = self._validate_wav_file(file_path)
        elif extension == 'flac':
            result = self._validate_flac_file(file_path)
        # Add more format-specific validators as needed
        
        return result
    
    def _validate_mp3_file(self, file_path: str) -> Dict[str, any]:
        """Validate MP3 file structure"""
        result = {'valid': True, 'errors': []}
        
        try:
            with open(file_path, 'rb') as f:
                # Check for ID3 tag or MP3 frame sync
                header = f.read(10)
                
                # Look for ID3 tag
                if header[:3] == b'ID3':
                    # ID3v2 tag found
                    if len(header) < 10 or header[3:6] == b'\x00\x00\x00':
                        result['errors'].append("Malformed ID3 tag")
                else:
                    # Check for MP3 frame sync (0xFFEx pattern)
                    frame_sync = (header[0] << 4) | (header[1] >> 4)
                    if frame_sync != 0xFFF:
                        result['errors'].append("No valid MP3 frame sync found")
        
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"MP3 validation failed: {str(e)}")
        
        return result
    
    def _validate_wav_file(self, file_path: str) -> Dict[str, any]:
        """Validate WAV file structure"""
        result = {'valid': True, 'errors': []}
        
        try:
            with open(file_path, 'rb') as f:
                # Check RIFF header
                riff_header = f.read(4)
                if riff_header != b'RIFF':
                    result['errors'].append("Invalid RIFF header")
                    result['valid'] = False
                    return result
                
                # Skip size and check WAVE format
                f.read(4)
                wave_header = f.read(4)
                if wave_header != b'WAVE':
                    result['errors'].append("Invalid WAVE header")
                    result['valid'] = False
        
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"WAV validation failed: {str(e)}")
        
        return result
    
    def _validate_flac_file(self, file_path: str) -> Dict[str, any]:
        """Validate FLAC file structure"""
        result = {'valid': True, 'errors': []}
        
        try:
            with open(file_path, 'rb') as f:
                # Check FLAC signature
                signature = f.read(4)
                if signature != b'fLaC':
                    result['errors'].append("Invalid FLAC signature")
                    result['valid'] = False
        
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"FLAC validation failed: {str(e)}")
        
        return result
    
    def _validate_file_integrity(self, file_path: str, file_info: Dict) -> Dict[str, any]:
        """Validate file integrity using basic checks"""
        result = {'valid': True, 'errors': []}
        
        try:
            # Check if file can be opened and read
            with open(file_path, 'rb') as f:
                # Read first and last few bytes
                f.seek(0)
                first_bytes = f.read(100)
                f.seek(-100, 2)  # Seek to 100 bytes from end
                last_bytes = f.read(100)
                
                # Basic sanity checks
                if not first_bytes:
                    result['errors'].append("Cannot read file header")
                    result['valid'] = False
                
                if not last_bytes:
                    result['errors'].append("Cannot read file footer")
                    result['valid'] = False
                
                # Check for null bytes in header (possible corruption)
                if b'\x00\x00\x00\x00' in first_bytes[:20]:
                    result['warnings'].append("File header contains suspicious null bytes")
        
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Integrity check failed: {str(e)}")
        
        return result
    
    def _validate_file_permissions(self, file_path: str) -> Dict[str, any]:
        """Validate file permissions"""
        result = {'valid': True, 'warnings': []}
        
        if not os.access(file_path, os.R_OK):
            result['warnings'].append("File is not readable")
        
        if not os.access(file_path, os.W_OK):
            result['warnings'].append("File is not writable")
        
        return result
    
    def calculate_file_hash(self, file_path: str, algorithm: str = 'sha256') -> str:
        """Calculate file hash for integrity verification"""
        hash_obj = hashlib.new(algorithm)
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_obj.update(chunk)
            return hash_obj.hexdigest()
        except Exception as e:
            raise FileProcessingError(f"Failed to calculate hash for {file_path}: {str(e)}")
    
    def is_supported_format(self, file_path: str) -> bool:
        """Quick check if file format is supported"""
        extension = Path(file_path).suffix.lower().lstrip('.')
        return extension in self.SUPPORTED_FORMATS
    
    def get_supported_formats(self) -> Set[str]:
        """Get set of supported file formats"""
        return set(self.SUPPORTED_FORMATS.keys())
    
    def get_format_info(self, file_path: str) -> Optional[Dict]:
        """Get information about file format"""
        extension = Path(file_path).suffix.lower().lstrip('.')
        return self.SUPPORTED_FORMATS.get(extension)
    
    def cleanup_temp_files(self, directory: str, pattern: str = "*.tmp") -> int:
        """Clean up temporary files in directory"""
        import glob
        
        cleaned_count = 0
        try:
            temp_files = glob.glob(os.path.join(directory, pattern))
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                    cleaned_count += 1
                    self.logger.info(f"Cleaned up temporary file: {temp_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up {temp_file}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error during temp file cleanup: {str(e)}")
        
        return cleaned_count


class AtomicFileOperation:
    """
    Wrapper for atomic file operations to prevent corruption
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def atomic_move(self, source: str, destination: str, overwrite: bool = False) -> bool:
        """
        Atomically move file from source to destination
        """
        import tempfile
        import shutil
        
        try:
            source_path = Path(source)
            dest_path = Path(destination)
            
            if dest_path.exists() and not overwrite:
                raise FileExistsError(f"Destination file already exists: {destination}")
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use temporary file for atomic operation
            temp_dest = dest_path.with_suffix(dest_path.suffix + '.tmp')
            
            try:
                # Copy to temporary location
                shutil.copy2(source, temp_dest)
                
                # Atomic move
                if dest_path.exists():
                    dest_path.unlink()
                temp_dest.rename(dest_path)
                
                self.logger.info(f"Successfully moved {source} to {destination}")
                return True
                
            except Exception as e:
                # Clean up temp file if operation failed
                if temp_dest.exists():
                    temp_dest.unlink()
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to move file from {source} to {destination}: {str(e)}")
            return False
    
    def atomic_write(self, file_path: str, data: bytes, backup: bool = True) -> bool:
        """
        Atomically write data to file with optional backup
        """
        import tempfile
        import shutil
        
        try:
            path_obj = Path(file_path)
            
            # Create directory if it doesn't exist
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Create temporary file
            temp_file = path_obj.with_suffix(path_obj.suffix + '.tmp')
            
            try:
                # Write to temporary file
                with open(temp_file, 'wb') as f:
                    f.write(data)
                
                # Create backup if requested and original exists
                backup_file = None
                if backup and path_obj.exists():
                    backup_file = path_obj.with_suffix(path_obj.suffix + '.backup')
                    shutil.copy2(path_obj, backup_file)
                
                # Atomic move
                if path_obj.exists():
                    path_obj.unlink()
                temp_file.rename(path_obj)
                
                self.logger.info(f"Successfully wrote data to {file_path}")
                return True
                
            except Exception as e:
                # Clean up temp file if operation failed
                if temp_file.exists():
                    temp_file.unlink()
                raise e
                
        except Exception as e:
            self.logger.error(f"Failed to write data to {file_path}: {str(e)}")
            return False