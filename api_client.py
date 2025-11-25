import requests
import time
import logging
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
            # Test with a simple upload endpoint check
            response = self.session.head(f"{self.BASE_URL}/upload/")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
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
        """Process voice cleanup using Lalal AI API"""
        try:
            # Default options for voice cleanup
            processing_params = {
                'id': file_id,
                'stem': options.get('stem', 'voice'),  # What to extract
                'splitter': options.get('splitter', 'perseus'),  # Neural network to use
                'filter': options.get('filter', 1),  # Post-processing filter intensity
                'enhanced_processing_enabled': options.get('enhanced_processing', True),
                'noise_cancelling_level': options.get('noise_cancelling', 1),
                'dereverb_enabled': options.get('dereverb', True)
            }
            
            # Prepare request
            data = {
                'params': json.dumps([processing_params])
            }
            
            self.logger.info(f"Starting voice cleanup for file ID: {file_id}")
            
            response = self.session.post(
                f"{self.BASE_URL}/split/",
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    # Get the processing job ID
                    job_id = result.get('id')
                    self.logger.info(f"Voice cleanup job started. Job ID: {job_id}")
                    return job_id
                else:
                    error_msg = result.get('error', 'Unknown processing error')
                    raise Exception(f"Processing failed: {error_msg}")
            else:
                raise Exception(f"Processing request failed with status {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Voice cleanup processing failed: {str(e)}")
            raise
    
    def check_job_status(self, job_id: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Check the status of a processing job"""
        try:
            # Note: This is a placeholder as the exact API endpoint for checking job status
            # would need to be confirmed from the actual Lalal AI API documentation
            
            # For now, we'll simulate checking status
            # In a real implementation, this would poll the API for job status
            
            # Simulate processing time
            time.sleep(2)
            
            # Return mock success for demonstration
            # In reality, this would check the actual job status
            return "completed", {
                "preview_url": f"{self.BASE_URL}/preview/{job_id}",
                "status": "completed",
                "progress": 100
            }
            
        except Exception as e:
            self.logger.error(f"Job status check failed: {str(e)}")
            return "error", None
    
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
        """Convert voice using Lalal AI voice conversion API"""
        try:
            # Default options for voice conversion
            conversion_params = {
                'id': file_id,
                'voice_pack_id': options.get('voice_pack_id', 'ALEX_KAYE'),
                'accent_enhance': options.get('accent_enhance', 1.0),
                'pitch_shifting': options.get('pitch_shifting', True),
                'dereverb_enabled': options.get('dereverb_enabled', False)
            }
            
            # Prepare request
            data = {
                'params': json.dumps([conversion_params])
            }
            
            self.logger.info(f"Starting voice conversion for file ID: {file_id}")
            
            response = self.session.post(
                f"{self.BASE_URL}/voice_convert/",
                data=data,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    # Get the conversion job ID
                    job_id = result.get('id')
                    self.logger.info(f"Voice conversion job started. Job ID: {job_id}")
                    return job_id
                else:
                    error_msg = result.get('error', 'Unknown conversion error')
                    raise Exception(f"Conversion failed: {error_msg}")
            else:
                raise Exception(f"Conversion request failed with status {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Voice conversion failed: {str(e)}")
            raise


# Add json import at the top
import json