import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from cryptography.fernet import Fernet
import base64
import logging

class ConfigManager:
    """Manages application configuration and secure credential storage"""
    
    def __init__(self):
        self.config_dir = Path.home() / '.lalalai_voice_cleaner'
        self.config_file = self.config_dir / 'config.json'
        self.key_file = self.config_dir / '.key'
        self.logger = logging.getLogger(__name__)
        
        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True)
        
        # Initialize encryption key
        self.cipher_suite = self._get_or_create_key()
    
    def _get_or_create_key(self) -> Fernet:
        """Get existing encryption key or create new one"""
        try:
            if self.key_file.exists():
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    key = f.read()
                return Fernet(key)
            else:
                # Generate new key
                key = Fernet.generate_key()
                with open(self.key_file, 'wb') as f:
                    f.write(key)
                # Set file permissions to be readable only by owner
                os.chmod(self.key_file, 0o600)
                return Fernet(key)
        except Exception as e:
            self.logger.error(f"Error managing encryption key: {str(e)}")
            raise
    
    def save_config(self, config: Dict[str, Any]) -> bool:
        """Save configuration to file with encryption for sensitive data"""
        try:
            # Load existing config if it exists
            existing_config = self.load_config() or {}
            
            # Merge new config with existing
            existing_config.update(config)
            
            # Encrypt sensitive data
            encrypted_config = self._encrypt_sensitive_data(existing_config)
            
            # Save to file
            with open(self.config_file, 'w') as f:
                json.dump(encrypted_config, f, indent=2)
            
            # Set file permissions to be readable only by owner
            os.chmod(self.config_file, 0o600)
            
            self.logger.info("Configuration saved successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration from file and decrypt sensitive data"""
        try:
            if not self.config_file.exists():
                return None
            
            with open(self.config_file, 'r') as f:
                encrypted_config = json.load(f)
            
            # Decrypt sensitive data
            config = self._decrypt_sensitive_data(encrypted_config)
            
            self.logger.info("Configuration loaded successfully")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading configuration: {str(e)}")
            return None
    
    def _encrypt_sensitive_data(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive configuration data"""
        encrypted_config = config.copy()
        
        # List of sensitive fields to encrypt
        sensitive_fields = ['license_key', 'api_key', 'password']
        
        for field in sensitive_fields:
            if field in config and config[field]:
                try:
                    # Encrypt the sensitive data
                    encrypted_value = self.cipher_suite.encrypt(
                        config[field].encode('utf-8')
                    )
                    # Store as base64 encoded string
                    encrypted_config[field] = base64.b64encode(encrypted_value).decode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Failed to encrypt {field}: {str(e)}")
        
        return encrypted_config
    
    def _decrypt_sensitive_data(self, encrypted_config: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive configuration data"""
        config = encrypted_config.copy()
        
        # List of sensitive fields to decrypt
        sensitive_fields = ['license_key', 'api_key', 'password']
        
        for field in sensitive_fields:
            if field in encrypted_config and encrypted_config[field]:
                try:
                    # Decode from base64
                    encrypted_value = base64.b64decode(encrypted_config[field].encode('utf-8'))
                    # Decrypt the sensitive data
                    decrypted_value = self.cipher_suite.decrypt(encrypted_value)
                    config[field] = decrypted_value.decode('utf-8')
                except Exception as e:
                    self.logger.warning(f"Failed to decrypt {field}: {str(e)}")
                    # Keep the encrypted value if decryption fails
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default fallback"""
        config = self.load_config()
        if config:
            return config.get(key, default)
        return default
    
    def set(self, key: str, value: Any) -> bool:
        """Set individual configuration value"""
        return self.save_config({key: value})
    
    def delete_config(self) -> bool:
        """Delete all configuration files"""
        try:
            if self.config_file.exists():
                self.config_file.unlink()
            if self.key_file.exists():
                self.key_file.unlink()
            
            self.logger.info("Configuration deleted successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting configuration: {str(e)}")
            return False
    
    def reset_encryption(self) -> bool:
        """Reset encryption key (will require re-entering sensitive data)"""
        try:
            # Delete existing key
            if self.key_file.exists():
                self.key_file.unlink()
            
            # Create new key
            self.cipher_suite = self._get_or_create_key()
            
            # Clear existing config since it can't be decrypted with new key
            if self.config_file.exists():
                self.config_file.unlink()
            
            self.logger.info("Encryption key reset successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error resetting encryption: {str(e)}")
            return False
    
    def get_config_info(self) -> Dict[str, Any]:
        """Get configuration information for display"""
        config = self.load_config()
        info = {
            'config_file_exists': self.config_file.exists(),
            'key_file_exists': self.key_file.exists(),
            'config_dir': str(self.config_dir),
            'has_license_key': bool(config and 'license_key' in config and config['license_key']),
            'has_input_folder': bool(config and 'input_folder' in config and config['input_folder']),
            'has_output_folder': bool(config and 'output_folder' in config and config['output_folder'])
        }
        return info
