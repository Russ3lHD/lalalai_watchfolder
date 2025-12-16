import requests
import time
import logging
import json
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

class LalalAIClient:
    """Client for interacting with Lalal AI API"""
    
    BASE_URL = "https://www.lalal.ai/api"
    
    def __init__(self, license_key: str):
        self.license_key = license_key
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'license {license_key}',
            'User-Agent': 'LalalAIVoiceCleaner/1.0.0'
        })
        self.logger = logging.getLogger(__name__)
    
    def test_connection(self) -> bool:
        """Test API connection and validate license"""
        try:
            # Use the billing/get-limits endpoint to validate license
            # This is the proper way to check if a license key is valid
            response = self.session.get(
                f"https://www.lalal.ai/billing/get-limits/",
                params={'key': self.license_key},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    # Log license info
                    option = result.get('option', 'Unknown')
                    email = result.get('email', 'Unknown')
                    minutes_left = result.get('process_duration_left', 0)
                    self.logger.info(f"License valid: {option} plan, {minutes_left:.1f} minutes remaining")
                    return True
                else:
                    error = result.get('error', 'Unknown error')
                    self.logger.error(f"License validation failed: {error}")
                    return False
            else:
                self.logger.error(f"License check returned status {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_license_info(self) -> Optional[Dict[str, Any]]:
        """Get detailed license information including remaining minutes"""
        try:
            response = self.session.get(
                f"https://www.lalal.ai/billing/get-limits/",
                params={'key': self.license_key},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    return {
                        'plan': result.get('option', 'Unknown'),
                        'email': result.get('email', 'Unknown'),
                        'total_minutes': result.get('process_duration_limit', 0),
                        'used_minutes': result.get('process_duration_used', 0),
                        'remaining_minutes': result.get('process_duration_left', 0)
                    }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get license info: {str(e)}")
            return None
    
    def upload_file(self, file_path: str) -> Optional[str]:
        """Upload file to Lalal AI server"""
        try:
            file_path_obj = Path(file_path)
            
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file size (10GB limit with license)
            file_size = file_path_obj.stat().st_size
            max_size = 10 * 1024 * 1024 * 1024  # 10GB
            
            if file_size > max_size:
                raise ValueError(f"File size ({file_size / (1024**3):.2f}GB) exceeds 10GB limit")
            
            # Prepare upload
            headers = {
                'Content-Disposition': f'attachment; filename={file_path_obj.name}',
                'Content-Type': 'application/octet-stream'
            }
            
            self.logger.info(f"Uploading file: {file_path_obj.name} ({file_size / (1024**2):.2f}MB)")
            
            with open(file_path, 'rb') as f:
                response = self.session.post(
                    f"{self.BASE_URL}/upload/",
                    data=f,
                    headers=headers,
                    timeout=300  # 5 minute timeout for large files
                )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    file_id = result.get('id')
                    duration = result.get('duration', 0)
                    self.logger.info(f"File uploaded successfully. ID: {file_id}, Duration: {duration}s")
                    return file_id
                else:
                    error_msg = result.get('error', 'Unknown upload error')
                    raise Exception(f"Upload failed: {error_msg}")
            else:
                raise Exception(f"Upload request failed with status {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"File upload failed: {str(e)}")
            raise
    
    def process_voice_cleanup(self, file_id: str, **options) -> Optional[str]:
        """Process voice cleanup using Lalal AI API
        
        Returns the file_id which is used to check status (not a separate job_id)
        """
        try:
            # Default options for voice cleanup
            processing_params = {
                'id': file_id,
                'stem': options.get('stem', 'voice'),  # What to extract
                'splitter': options.get('splitter', 'orion'),  # Neural network to use
                'dereverb_enabled': options.get('dereverb', False),
            }
            
            # Add stem-specific options
            if options.get('stem') == 'voice':
                processing_params['noise_cancelling_level'] = options.get('noise_cancelling', 1)
            else:
                processing_params['enhanced_processing_enabled'] = options.get('enhanced_processing', False)
            
            self.logger.info(f"Starting voice cleanup for file ID: {file_id}")
            self.logger.info(f"Split request params: {processing_params}")
            
            # Send as form-urlencoded with params as JSON string
            response = self.session.post(
                f"{self.BASE_URL}/split/",
                data={'params': json.dumps([processing_params])},
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Split API response: {result}")
                if result.get('status') == 'success':
                    # The file_id is used to check status, not a separate job_id
                    self.logger.info(f"Voice cleanup started for file ID: {file_id}")
                    return file_id  # Return file_id to use with check endpoint
                else:
                    error_msg = result.get('error', 'Unknown processing error')
                    raise Exception(f"Processing failed: {error_msg}")
            else:
                raise Exception(f"Processing request failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Voice cleanup processing failed: {str(e)}")
            raise
    
    def check_job_status(self, file_id: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Check the status of a processing job using /api/check/ endpoint"""
        try:
            response = self.session.post(
                f"{self.BASE_URL}/check/",
                data={'id': file_id},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.debug(f"Check API response: {result}")
                
                if result.get('status') == 'error':
                    error = result.get('error', 'Unknown error')
                    self.logger.error(f"Check status error: {error}")
                    return "error", {"error": error}
                
                # Get the file result from the nested structure
                file_result = result.get('result', {}).get(file_id, {})
                
                if not file_result:
                    # Try checking if result is directly the file data
                    file_result = result
                
                if file_result.get('status') == 'error':
                    return "error", {"error": file_result.get('error', 'Unknown error')}
                
                # Check task state
                task = file_result.get('task')
                if task:
                    task_state = task.get('state')
                    
                    if task_state == 'success':
                        # Processing completed, get download URLs
                        split_data = file_result.get('split', {})
                        return "completed", {
                            "stem_track": split_data.get('stem_track'),
                            "stem_track_size": split_data.get('stem_track_size'),
                            "back_track": split_data.get('back_track'),
                            "back_track_size": split_data.get('back_track_size'),
                            "duration": split_data.get('duration'),
                            "stem": split_data.get('stem')
                        }
                    
                    elif task_state == 'error':
                        return "error", {"error": task.get('error', 'Processing error')}
                    
                    elif task_state == 'progress':
                        progress = task.get('progress', 0)
                        return "processing", {"progress": progress}
                    
                    elif task_state == 'cancelled':
                        return "cancelled", None
                
                # No task yet, still queued
                return "processing", {"progress": 0}
                
            else:
                raise Exception(f"Check request failed with status {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Job status check failed: {str(e)}")
            return "error", {"error": str(e)}
    
    def download_processed_file(self, file_url: str, output_path: str) -> bool:
        """Download processed file from Lalal AI"""
        try:
            self.logger.info(f"Downloading processed file from: {file_url}")
            
            response = self.session.get(file_url, stream=True, timeout=300)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                self.logger.info(f"File downloaded successfully: {output_path}")
                return True
            else:
                raise Exception(f"Download failed with status {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"File download failed: {str(e)}")
            return False
    
    def get_supported_formats(self) -> list:
        """Get list of supported audio formats"""
        # Based on Lalal AI API documentation
        return [
            'mp3', 'wav', 'flac', 'm4a', 'ogg', 'wma', 'aac', 'aiff', 'au', 'ra', 'ram'
        ]
    
    def is_format_supported(self, file_path: str) -> bool:
        """Check if file format is supported"""
        try:
            file_ext = Path(file_path).suffix.lower().lstrip('.')
            supported_formats = self.get_supported_formats()
            return file_ext in supported_formats
        except Exception:
            return False

    def list_voice_packs(self) -> Optional[Dict[str, Any]]:
        """List available voice packs"""
        try:
            response = self.session.get(f"{self.BASE_URL}/voice_packs/list/")
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to list voice packs: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Voice pack listing failed: {str(e)}")
            return None

    def convert_voice(self, file_id: str, **options) -> Optional[str]:
        """Convert voice using Lalal AI voice conversion API
        
        Returns file_id to use with check_voice_conversion_status
        """
        try:
            # API uses form data, not JSON params for voice conversion
            form_data = {
                'id': file_id,
                'voice': options.get('voice_pack_id', 'ALEX_KAYE'),
                'accent_enhance': options.get('accent_enhance', 1.0),
                'pitch_shifting': 'true' if options.get('pitch_shifting', True) else 'false',
                'dereverb_enabled': 'true' if options.get('dereverb_enabled', False) else 'false'
            }
            
            self.logger.info(f"Starting voice conversion for file ID: {file_id}")
            self.logger.info(f"Voice conversion params: {form_data}")
            
            response = self.session.post(
                f"{self.BASE_URL}/change_voice/",
                data=form_data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Voice conversion response: {result}")
                if result.get('status') == 'success':
                    # Return file_id to check status
                    returned_id = result.get('id', file_id)
                    self.logger.info(f"Voice conversion started. File ID: {returned_id}")
                    return returned_id
                else:
                    error_msg = result.get('error', 'Unknown conversion error')
                    raise Exception(f"Conversion failed: {error_msg}")
            else:
                raise Exception(f"Conversion request failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Voice conversion failed: {str(e)}")
            raise


# Add json import at the top
import json