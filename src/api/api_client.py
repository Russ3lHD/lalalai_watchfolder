import requests
import time
import logging
import json
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

class LalalAIClient:
    """Client for interacting with Lalal AI API"""
    
    BASE_URL = "https://www.lalal.ai/api/v1/"
    
    def __init__(self, license_key: str):
        self.license_key = license_key
        self.session = requests.Session()
        # Use the v1 authentication header
        self.session.headers.update({
            'X-License-Key': license_key,
            'User-Agent': 'LalalAIVoiceCleaner/1.0.0'
        })
        self.logger = logging.getLogger(__name__)
    
    def test_connection(self) -> bool:
        """Test API connection and validate license (v1).
        Uses a small, documented v1 endpoint to validate license/auth.
        """
        try:
            # Validate license by calling voice_packs/list/ (v1). 200 == reachable/authorized.
            response = self.session.post(
                f"{self.BASE_URL}voice_packs/list/",
                json={},
                timeout=30
            )

            if response.status_code == 200:
                self.logger.info("License validated (voice_packs/list returned 200)")
                return True
            elif response.status_code in (401, 403):
                self.logger.error(f"Authentication failed: {response.status_code}")
                return False
            else:
                self.logger.error(f"License check returned status {response.status_code}")
                return False

        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def get_license_info(self) -> Optional[Dict[str, Any]]:
        """Get license / account related info. Uses v1 endpoints where available.
        Note: v1 does not always expose the same billing fields; return best-effort info.
        """
        try:
            response = self.session.post(
                f"{self.BASE_URL}voice_packs/list/",
                json={},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json() or {}
                packs = data.get('packs', [])
                return {
                    'voice_packs_count': len(packs),
                    'voice_packs': packs
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
                    f"{self.BASE_URL}upload/",
                    data=f,
                    headers=headers,
                    timeout=300  # 5 minute timeout for large files
                )

            if response.status_code in (200, 201):
                result = response.json() or {}
                # Accept both v1 and legacy response shapes
                if result.get('status') == 'success' or 'id' in result or 'source_id' in result or 'sourceId' in result:
                    file_id = result.get('id') or result.get('source_id') or result.get('sourceId')
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
            # Accept legacy synonym 'voice'. Internally we map 'voice' -> 'vocals' for
            # the stem-separator endpoints, but the dedicated `voice_clean` endpoint
            # expects the literal value 'voice' for spoken/background-noise cleanup.
            requested_stem = options.get('stem', 'voice')
            _stem_map = {'voice': 'vocals'}
            stem = _stem_map.get(requested_stem, requested_stem)

            allowed_stems = {
                'vocals', 'drum', 'piano', 'bass', 'electric_guitar',
                'acoustic_guitar', 'synthesizer', 'strings', 'wind'
            }
            if stem not in allowed_stems:
                raise ValueError(f"Invalid stem '{requested_stem}'. Allowed values: {sorted(list(allowed_stems))}")

            processing_params = {
                'id': file_id,
                'stem': stem,  # mapped/canonical value sent to API
                'splitter': options.get('splitter', 'orion'),  # Neural network to use
                'dereverb_enabled': options.get('dereverb', False),
            }

            # Add stem-specific options
            if stem == 'vocals':
                # UI/config uses 0=Mild, 1=Normal, 2=Aggressive — translate to API's 1..3 range
                local_nc = int(options.get('noise_cancelling', 1))
                api_noise_level = max(1, min(local_nc + 1, 3))
                processing_params['noise_cancelling_level'] = api_noise_level
            else:
                processing_params['enhanced_processing_enabled'] = options.get('enhanced_processing', False)

            self.logger.info(f"Starting voice cleanup for file ID: {file_id} (requested_stem={requested_stem} -> stem={stem})")
            self.logger.info(f"Split request params: {processing_params}")

            # For spoken/background-noise cleanup use the dedicated voice_clean endpoint.
            # Preserve compatibility by sending the same `presets` shape that the API expects.
            payload = {
                "source_id": file_id,
                "presets": {
                    # If user explicitly requested `stem='voice'` send the literal
                    # 'voice' (voice_clean expects 'voice'); otherwise send the
                    # mapped/canonical stem (e.g. 'vocals').
                    "stem": 'voice' if requested_stem == 'voice' else processing_params.get('stem'),
                    "dereverb_enabled": bool(processing_params.get('dereverb_enabled', False))
                }
            }

            # Add stem-specific fields
            if 'noise_cancelling_level' in processing_params:
                payload['presets']['noise_cancelling_level'] = processing_params['noise_cancelling_level']
            if 'enhanced_processing_enabled' in processing_params:
                payload['presets']['enhanced_processing_enabled'] = processing_params['enhanced_processing_enabled']
            if processing_params.get('splitter'):
                payload['presets']['splitter'] = processing_params.get('splitter')

            response = self.session.post(
                f"{self.BASE_URL}split/voice_clean/",
                json=payload,
                timeout=60
            )

            if response.status_code in (200, 201):
                result = response.json() or {}
                self.logger.info(f"Split API response: {result}")
                # v1 returns a task_id; fall back to returning source_id for legacy
                task_id = result.get('task_id') or result.get('id')
                if task_id:
                    self.logger.info(f"Voice cleanup task started. Task ID: {task_id}")
                    return task_id
                # If API returned legacy success flag, return source file id so check works
                if result.get('status') == 'success':
                    self.logger.info(f"Voice cleanup acknowledged for source: {file_id}")
                    return file_id
                raise Exception(f"Processing failed: unexpected response shape: {result}")
            else:
                raise Exception(f"Processing request failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Voice cleanup processing failed: {str(e)}")
            raise
    
    def check_job_status(self, file_id: str) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Check the status of a processing job using /api/check/ endpoint"""
        try:
            # v1-style check: send task_ids list and adapt to both v1 and legacy response shapes
            response = self.session.post(
                f"{self.BASE_URL}check/",
                json={"task_ids": [file_id]},
                timeout=30
            )

            if response.status_code == 200:
                data = response.json() or {}
                self.logger.debug(f"Check API response: {data}")

                # Try v1-style result first
                v1_result = data.get('result', {}).get(file_id)
                if v1_result:
                    status = v1_result.get('status')
                    if status == 'success':
                        tracks = v1_result.get('result', {}).get('tracks', [])
                        # map track labels to URLs
                        mapping = {}
                        for t in tracks:
                            label = t.get('label') or t.get('stem') or t.get('type')
                            url = t.get('url') or t.get('download_url')
                            if label and url:
                                mapping[label] = url
                        stem = mapping.get('stem_track') or mapping.get('vocals') or (tracks[0].get('url') if tracks else None)
                        back = mapping.get('back_track') or mapping.get('backing')
                        return "completed", {
                            "stem_track": stem,
                            "back_track": back,
                            "tracks": tracks,
                            "duration": v1_result.get('result', {}).get('duration')
                        }
                    elif status == 'progress':
                        return "processing", {"progress": v1_result.get('progress', 0)}
                    elif status == 'error':
                        return "error", {"error": v1_result.get('error') or v1_result.get('message')}
                    elif status == 'cancelled':
                        return "cancelled", None

                # Fallback to legacy parsing (existing shape)
                result = data
                if result.get('status') == 'error':
                    return "error", {"error": result.get('error', 'Unknown error')}

                file_result = result.get('result', {}).get(file_id, {}) or result
                if file_result.get('status') == 'error':
                    return "error", {"error": file_result.get('error', 'Unknown error')}

                task = file_result.get('task')
                if task:
                    task_state = task.get('state')
                    if task_state == 'success':
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
                        return "processing", {"progress": task.get('progress', 0)}
                    elif task_state == 'cancelled':
                        return "cancelled", None

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
        """List available voice packs (v1)."""
        try:
            response = self.session.post(f"{self.BASE_URL}voice_packs/list/", json={}, timeout=15)
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Failed to list voice packs: {response.status_code}")
        except Exception as e:
            self.logger.error(f"Voice pack listing failed: {str(e)}")
            return None

    def delete_files(self, source_ids: list) -> bool:
        """Delete files from LALAL.AI storage (v1 delete/ endpoint)."""
        try:
            response = self.session.post(f"{self.BASE_URL}delete/", json={"source_ids": source_ids}, timeout=15)
            if response.status_code == 200:
                return True
            else:
                self.logger.error(f"Failed to delete files: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            self.logger.error(f"Delete files failed: {str(e)}")
            return False

    def convert_voice(self, file_id: str, **options) -> Optional[str]:
        """Convert voice using Lalal AI voice conversion API
        
        Returns file_id to use with check_voice_conversion_status
        """
        try:
            # API uses form data, not JSON params for voice conversion
            payload = {
                'source_id': file_id,
                'presets': {
                    'voice_pack_id': options.get('voice_pack_id', 'ALEX_KAYE'),
                    'accent': options.get('accent_enhance', 1.0),
                    'tonality_reference': options.get('tonality_reference', 'source_file'),
                    'dereverb_enabled': bool(options.get('dereverb_enabled', False))
                }
            }

            self.logger.info(f"Starting voice conversion for file ID: {file_id}")
            self.logger.info(f"Voice conversion params: {payload}")

            response = self.session.post(
                f"{self.BASE_URL}change_voice/",
                json=payload,
                timeout=60
            )

            if response.status_code in (200, 201):
                result = response.json() or {}
                self.logger.info(f"Voice conversion response: {result}")
                # v1 returns a task_id
                task_id = result.get('task_id') or result.get('id')
                if task_id:
                    self.logger.info(f"Voice conversion started. Task ID: {task_id}")
                    return task_id
                raise Exception(f"Conversion failed: unexpected response {result}")
            else:
                raise Exception(f"Conversion request failed with status {response.status_code}: {response.text}")
                
        except Exception as e:
            self.logger.error(f"Voice conversion failed: {str(e)}")
            raise


