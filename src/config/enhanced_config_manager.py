"""
Enhanced configuration manager with validation, schema checking, and migration
Provides robust configuration management with backup/restore capabilities
"""

import json
import os
import shutil
import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import copy
from cryptography.fernet import Fernet
import base64

from src.utils.exceptions import (
    ConfigurationError, ConfigurationValidationError,
    ConfigurationEncryptionError, ConfigurationFileError
)
from src.utils.file_validator import AtomicFileOperation


class ConfigSchema:
    """Configuration schema definition and validation"""
    
    def __init__(self):
        self.schema = {
            'license_key': {
                'type': str,
                'required': False,
                'encrypted': True,
                'min_length': 10,
                'description': 'Lalal AI license key'
            },
            'input_folder': {
                'type': str,
                'required': False,
                'path_exists': True,
                'description': 'Input folder path for audio files'
            },
            'output_folder': {
                'type': str,
                'required': False,
                'writable': True,
                'description': 'Output folder path for processed files'
            },
            'auto_start': {
                'type': bool,
                'default': False,
                'description': 'Auto-start watching on launch'
            },
            'create_processed_folder': {
                'type': bool,
                'default': True,
                'description': 'Create processed subfolder'
            },
            'enhanced_processing': {
                'type': bool,
                'default': True,
                'description': 'Enable enhanced processing'
            },
            'noise_cancelling': {
                'type': int,
                'default': 1,
                'min_value': 0,
                'max_value': 2,
                'description': 'Noise cancelling level (0-2)'
            },
            'dereverb': {
                'type': bool,
                'default': True,
                'description': 'Enable dereverb (remove echo)'
            },
            'stem': {
                'type': str,
                'default': 'voice',
                'choices': ['vocals', 'voice', 'drum', 'bass', 'piano', 
                           'electric_guitar', 'acoustic_guitar', 'synthesizer', 
                           'strings', 'wind'],
                'description': 'Stem to extract'
            },
            'splitter': {
                'type': str,
                'default': 'perseus',
                'choices': ['auto', 'phoenix', 'orion', 'perseus', 'andromeda'],
                'description': 'Neural network to use'
            },
            'filter': {
                'type': int,
                'default': 1,
                'min_value': 0,
                'max_value': 2,
                'description': 'Post-processing filter intensity'
            },
            'processing_mode': {
                'type': str,
                'default': 'voice_cleanup',
                'choices': ['voice_cleanup'],
                'description': 'Processing mode'
            },
            'max_queue_size': {
                'type': int,
                'default': 100,
                'min_value': 1,
                'max_value': 1000,
                'description': 'Maximum processing queue size'
            },
            'retry_attempts': {
                'type': int,
                'default': 3,
                'min_value': 1,
                'max_value': 10,
                'description': 'Number of retry attempts for failed operations'
            },
            'timeout_seconds': {
                'type': int,
                'default': 300,
                'min_value': 30,
                'max_value': 3600,
                'description': 'Timeout for operations in seconds'
            },
            'health_check_interval': {
                'type': int,
                'default': 30,
                'min_value': 5,
                'max_value': 300,
                'description': 'Health check interval in seconds'
            }
        }
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration against schema
        
        Returns:
            Dict with validation results and any default values applied
        """
        result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'validated_config': {},
            'defaults_applied': []
        }
        
        try:
            validated_config = {}
            
            # Process each field in schema
            for field_name, field_config in self.schema.items():
                value = config.get(field_name)
                
                # Apply defaults if field is missing and has a default
                if value is None and 'default' in field_config:
                    value = field_config['default']
                    validated_config[field_name] = value
                    result['defaults_applied'].append(field_name)
                    continue
                
                # Skip validation for missing optional fields
                if value is None and not field_config.get('required', False):
                    continue
                
                # Validate required fields
                if value is None and field_config.get('required', False):
                    result['is_valid'] = False
                    result['errors'].append(f"Required field '{field_name}' is missing")
                    continue
                
                if value is not None:
                    # Type validation
                    if not isinstance(value, field_config['type']):
                        result['is_valid'] = False
                        result['errors'].append(
                            f"Field '{field_name}' must be of type {field_config['type'].__name__}, "
                            f"got {type(value).__name__}"
                        )
                        continue
                    
                    # Range validation for numeric types
                    if field_config['type'] in (int, float):
                        if 'min_value' in field_config and value < field_config['min_value']:
                            result['is_valid'] = False
                            result['errors'].append(
                                f"Field '{field_name}' must be >= {field_config['min_value']}, got {value}"
                            )
                        if 'max_value' in field_config and value > field_config['max_value']:
                            result['is_valid'] = False
                            result['errors'].append(
                                f"Field '{field_name}' must be <= {field_config['max_value']}, got {value}"
                            )
                    
                    # String validation
                    if field_config['type'] == str:
                        if 'min_length' in field_config and len(value) < field_config['min_length']:
                            result['is_valid'] = False
                            result['errors'].append(
                                f"Field '{field_name}' must be at least {field_config['min_length']} characters, "
                                f"got {len(value)}"
                            )
                        if 'choices' in field_config and value not in field_config['choices']:
                            result['is_valid'] = False
                            result['errors'].append(
                                f"Field '{field_name}' must be one of {field_config['choices']}, got '{value}'"
                            )
                    
                    # Path validation
                    if field_config.get('path_exists') and not os.path.exists(value):
                        result['warnings'].append(f"Path does not exist: {value}")
                    
                    if field_config.get('writable') and not os.access(value, os.W_OK):
                        if os.path.exists(value):
                            result['warnings'].append(f"Path is not writable: {value}")
                        else:
                            # Try to create parent directories
                            try:
                                Path(value).parent.mkdir(parents=True, exist_ok=True)
                            except Exception as e:
                                result['warnings'].append(f"Cannot create path: {value} - {str(e)}")
            
            result['validated_config'] = validated_config
            return result
            
        except Exception as e:
            result['is_valid'] = False
            result['errors'].append(f"Validation failed: {str(e)}")
            return result


class EnhancedConfigManager:
    """
    Enhanced configuration manager with validation, backup, and migration support
    """
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / '.lalalai_voice_cleaner'
        self.config_file = self.config_dir / 'config.json'
        self.backup_dir = self.config_dir / 'backups'
        self.key_file = self.config_dir / '.key'
        self.schema = ConfigSchema()
        self.atomic_ops = AtomicFileOperation()
        self.logger = logging.getLogger(__name__)
        
        # Ensure directories exist
        self.config_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
        
        # Initialize encryption
        self.cipher_suite = self._get_or_create_key()
        
        # Configuration state
        self._config_cache = None
        self._cache_timestamp = 0
        
        self.logger.info(f"Enhanced config manager initialized with config dir: {self.config_dir}")
    
    def _get_or_create_key(self) -> Fernet:
        """Get existing encryption key or create new one"""
        try:
            if self.key_file.exists():
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                return Fernet(key)
            else:
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                os.chmod(self.key_file, 0o600)
                return Fernet(key)
        except Exception as e:
            self.logger.error(f"Error managing encryption key: {str(e)}")
            raise ConfigurationEncryptionError(f"Failed to manage encryption key: {str(e)}")
    
    def save_config(self, config: Dict[str, Any], create_backup: bool = True) -> bool:
        """
        Save configuration with validation and backup
        
        Args:
            config: Configuration dictionary
            create_backup: Whether to create a backup before saving
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Validate configuration
            validation_result = self.schema.validate_config(config)
            
            if not validation_result['is_valid']:
                error_msg = "Configuration validation failed: " + "; ".join(validation_result['errors'])
                raise ConfigurationValidationError(error_msg, validation_result['errors'])
            
            if validation_result['warnings']:
                self.logger.warning(f"Configuration warnings: {validation_result['warnings']}")
            
            # Create backup if requested and config exists
            if create_backup and self.config_file.exists():
                self._create_backup()
            
            # Use validated config
            validated_config = validation_result['validated_config']
            
            # Encrypt sensitive data
            encrypted_config = self._encrypt_sensitive_data(validated_config)
            
            # Add metadata
            encrypted_config['_metadata'] = {
                'version': '2.0',
                'saved_at': datetime.now().isoformat(),
                'schema_version': '1.0'
            }
            
            # Atomic write
            config_json = json.dumps(encrypted_config, indent=2)
            success = self.atomic_ops.atomic_write(str(self.config_file), config_json.encode('utf-8'))
            
            if success:
                self._config_cache = validated_config.copy()
                self._cache_timestamp = time.time()
                os.chmod(self.config_file, 0o600)
                
                self.logger.info("Configuration saved successfully")
                if validation_result['defaults_applied']:
                    self.logger.info(f"Applied defaults for: {validation_result['defaults_applied']}")
                
                return True
            else:
                raise ConfigurationFileError("Failed to write configuration file")
                
        except ConfigurationValidationError:
            raise
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            raise ConfigurationFileError(f"Failed to save configuration: {str(e)}")
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        Load and validate configuration
        
        Returns:
            Configuration dictionary or None if not found
        """
        try:
            # Check cache first
            if self._config_cache and (time.time() - self._cache_timestamp) < 60:
                return self._config_cache.copy()
            
            if not self.config_file.exists():
                self.logger.info("Configuration file does not exist")
                return None
            
            # Read and decrypt configuration
            with open(self.config_file, 'r') as f:
                encrypted_config = json.load(f)
            
            # Remove metadata before decryption
            metadata = encrypted_config.get('_metadata', {})
            encrypted_config.pop('_metadata', None)
            
            # Decrypt sensitive data
            config = self._decrypt_sensitive_data(encrypted_config)
            
            # Validate loaded configuration
            validation_result = self.schema.validate_config(config)
            
            if not validation_result['is_valid']:
                self.logger.warning(f"Loaded configuration has validation issues: {validation_result['errors']}")
                # Don't fail completely, just log warnings
            
            # Apply any missing defaults
            for field_name, field_config in self.schema.schema.items():
                if field_name not in config and 'default' in field_config:
                    config[field_name] = field_config['default']
                    self.logger.info(f"Applied default value for {field_name}: {field_config['default']}")
            
            # Cache the configuration
            self._config_cache = config.copy()
            self._cache_timestamp = time.time()
            
            self.logger.info("Configuration loaded successfully")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            raise ConfigurationFileError(f"Failed to load configuration: {str(e)}")
    
    def _encrypt_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive configuration data"""
        encrypted_config = config.copy()
        
        sensitive_fields = ['license_key', 'api_key', 'password']
        
        for field in sensitive_fields:
            if field in config and config[field]:
                try:
                    encrypted_value = self.cipher_suite.encrypt(
                        config[field].encode('utf-8')
                    )
                    encrypted_config[field] = base64.b64encode(encrypted_value).decode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Failed to encrypt {field}: {str(e)}")
        
        return encrypted_config
    
    def _decrypt_sensitive_data(self, encrypted_config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive configuration data"""
        config = encrypted_config.copy()
        
        sensitive_fields = ['license_key', 'api_key', 'password']
        
        for field in sensitive_fields:
            if field in encrypted_config and encrypted_config[field]:
                try:
                    encrypted_value = base64.b64decode(encrypted_config[field].encode('utf-8'))
                    decrypted_value = self.cipher_suite.decrypt(encrypted_value)
                    config[field] = decrypted_value.decode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Failed to decrypt {field}: {str(e)}")
        
        return config
    
    def _create_backup(self):
        """Create a timestamped backup of current configuration"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"config_backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            shutil.copy2(self.config_file, backup_path)
            
            # Keep only last 10 backups
            backups = sorted(self.backup_dir.glob("config_backup_*.json"))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()
            
            self.logger.info(f"Created configuration backup: {backup_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
    
    def restore_backup(self, backup_timestamp: Optional[str] = None) -> bool:
        """
        Restore configuration from backup
        
        Args:
            backup_timestamp: Specific backup to restore (format: YYYYMMDD_HHMMSS)
                            If None, restores from most recent backup
            
        Returns:
            True if restored successfully, False otherwise
        """
        try:
            backups = sorted(self.backup_dir.glob("config_backup_*.json"))
            
            if not backups:
                raise ConfigurationFileError("No backups found")
            
            if backup_timestamp:
                backup_path = self.backup_dir / f"config_backup_{backup_timestamp}.json"
                if not backup_path.exists():
                    raise ConfigurationFileError(f"Backup not found: {backup_timestamp}")
            else:
                backup_path = backups[-1]  # Most recent backup
            
            # Validate backup file
            try:
                with open(backup_path, 'r') as f:
                    backup_config = json.load(f)
            except Exception as e:
                raise ConfigurationFileError(f"Invalid backup file: {str(e)}")
            
            # Create backup of current config before restoring
            if self.config_file.exists():
                self._create_backup()
            
            # Restore the backup
            shutil.copy2(backup_path, self.config_file)
            
            # Clear cache
            self._config_cache = None
            self._cache_timestamp = 0
            
            self.logger.info(f"Restored configuration from backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {str(e)}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List available configuration backups"""
        backups = []
        
        try:
            for backup_path in sorted(self.backup_dir.glob("config_backup_*.json")):
                stat = backup_path.stat()
                backups.append({
                    'timestamp': backup_path.stem.replace('config_backup_', ''),
                    'file_path': str(backup_path),
                    'size': stat.st_size,
                    'created': stat.st_ctime
                })
        except Exception as e:
            self.logger.error(f"Error listing backups: {str(e)}")
        
        return backups
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default fallback"""
        config = self.load_config()
        if config:
            return config.get(key, default)
        return default
    
    def set(self, key: str, value: Any) -> bool:
        """Set individual configuration value"""
        config = self.load_config() or {}
        config[key] = value
        return self.save_config(config)
    
    def delete_config(self) -> bool:
        """Delete all configuration files"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            if self.key_file.exists():
                self.key_file.unlink()
            
            # Clear cache
            self._config_cache = None
            self._cache_timestamp = 0
            
            self.logger.info("Configuration deleted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting configuration: {str(e)}")
            return False
    
    def export_config(self, export_path: Path, include_sensitive: bool = False) -> bool:
        """Export configuration to file (optionally excluding sensitive data)"""
        try:
            config = self.load_config()
            if not config:
                raise ConfigurationError("No configuration to export")
            
            export_config = config.copy()
            
            if not include_sensitive:
                # Remove sensitive fields
                sensitive_fields = ['license_key', 'api_key', 'password']
                for field in sensitive_fields:
                    export_config.pop(field, None)
            
            # Add export metadata
            export_config['_export_info'] = {
                'exported_at': datetime.now().isoformat(),
                'version': '2.0',
                'include_sensitive': include_sensitive
            }
            
            export_data = json.dumps(export_config, indent=2)
            
            success = self.atomic_ops.atomic_write(str(export_path), export_data.encode('utf-8'))
            
            if success:
                self.logger.info(f"Configuration exported to {export_path}")
                return True
            else:
                raise ConfigurationFileError("Failed to write export file")
                
        except Exception as e:
            self.logger.error(f"Error exporting configuration: {str(e)}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration information for display"""
        config = self.load_config()
        backups = self.list_backups()
        
        info = {
            'config_file_exists': self.config_file.exists(),
            'config_file_path': str(self.config_file),
            'config_dir': str(self.config_dir),
            'backup_dir': str(self.backup_dir),
            'backups_count': len(backups),
            'has_license_key': bool(config and 'license_key' in config and config['license_key']),
            'has_input_folder': bool(config and 'input_folder' in config and config['input_folder']),
            'has_output_folder': bool(config and 'output_folder' in config and config['output_folder']),
            'last_modified': self.config_file.stat().st_mtime if self.config_file.exists() else None,
            'cache_valid': self._config_cache is not None
        }
        
        if config:
            info['config_keys'] = list(config.keys())
            info['config_size'] = len(str(config))
        
        return info