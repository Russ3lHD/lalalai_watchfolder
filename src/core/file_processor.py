import os
import time
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any
from queue import Queue, Empty
from datetime import datetime

from ..api import LalalAIClient

class FileProcessor:
    """Processes audio files using Lalal AI API"""
    
    def __init__(self, api_client, output_folder: str, app_instance, shutdown_coordinator=None):
        self.api_client = api_client
        self.output_folder = output_folder
        self.app_instance = app_instance
        self.shutdown_coordinator = shutdown_coordinator
        self.processing_queue = Queue()
        self.is_processing = False
        self.processing_thread: Optional[threading.Thread] = None
        self.current_operation_id: Optional[str] = None
        self.logger = logging.getLogger(__name__)
        
        # Processing statistics
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'processing_time': 0.0
        }
        
        # Create processed subfolder for original files
        self.processed_folder = os.path.join(output_folder, 'processed_originals')
        os.makedirs(self.processed_folder, exist_ok=True)
    
    def process_file(self, file_path: str):
        """Add file to processing queue"""
        try:
            # Validate file
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check file format support
            if not self.api_client.is_format_supported(file_path):
                raise ValueError(f"Unsupported file format: {file_path}")
            
            # Add to queue
            self.processing_queue.put(file_path)
            self.logger.info(f"File added to processing queue: {file_path}")
            
            # Start processing if not already running
            if not self.is_processing:
                self.start_processing()
            
            # Update UI
            if self.app_instance:
                queue_size = self.processing_queue.qsize()
                self.app_instance.update_processing_status(f"Queued ({queue_size} files)")
            
        except Exception as e:
            self.logger.error(f"Error adding file to queue: {str(e)}")
            if self.app_instance:
                self.app_instance.log_message(f"Failed to queue file: {str(e)}", "error")
    
    def start_processing(self):
        """Start the processing thread"""
        if self.is_processing:
            self.logger.warning("File processor is already running")
            return
        
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self.processing_thread.start()
        self.logger.info("File processor started")
    
    def stop_processing(self):
        """Stop the processing thread"""
        self.is_processing = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=10)  # Wait up to 10 seconds
            self.processing_thread = None
        
        self.logger.info("File processor stopped")
    
    def _processing_loop(self):
        """Main processing loop"""
        self.logger.info("Processing loop started")
        
        while self.is_processing:
            try:
                # Get file from queue (timeout to allow checking is_processing)
                file_path = self.processing_queue.get(timeout=1)
                
                # Process the file
                self._process_single_file(file_path)
                
                # Mark task as done
                self.processing_queue.task_done()
                
            except Empty:
                # No files in queue, continue loop
                continue
            except Exception as e:
                self.logger.error(f"Error in processing loop: {str(e)}")
                if self.app_instance:
                    self.app_instance.log_message(f"Processing error: {str(e)}", "error")
        
        self.logger.info("Processing loop ended")
    
    def _process_single_file(self, file_path: str):
        """Process a single audio file"""
        start_time = time.time()
        file_name = Path(file_path).name
        
        try:
            self.logger.info(f"Starting processing of: {file_name}")
            
            # Update UI
            if self.app_instance:
                self.app_instance.update_processing_status(f"Processing: {file_name}")
                self.app_instance.log_message(f"Processing file: {file_name}")
            
            # Process using API
            # Step 1: Upload file
            self.logger.info(f"Uploading file: {file_name}")
            if self.app_instance:
                self.app_instance.log_message(f"Uploading file: {file_name}")
            
            file_id = self.api_client.upload_file(file_path)
            
            if not file_id:
                raise Exception("File upload failed")
            
            self.logger.info(f"File uploaded successfully. ID: {file_id}")
            if self.app_instance:
                self.app_instance.log_message(f"File uploaded successfully")
            
            # Step 2: Process based on mode
            processing_mode = self.app_instance.config_manager.get('processing_mode', 'voice_cleanup')
            
            if processing_mode == 'voice_cleanup':
                self.logger.info(f"Starting voice cleanup for: {file_name}")
                if self.app_instance:
                    self.app_instance.log_message(f"Starting voice cleanup")
                
                # Get voice cleanup settings from configuration
                enhanced_processing = self.app_instance.config_manager.get('enhanced_processing', True)
                noise_cancelling = self.app_instance.config_manager.get('noise_cancelling', 1)
                dereverb = self.app_instance.config_manager.get('dereverb', True)
                stem = self.app_instance.config_manager.get('stem', 'voice')
                splitter = self.app_instance.config_manager.get('splitter', 'perseus')
                filter_level = self.app_instance.config_manager.get('filter', 1)
                
                job_id = self.api_client.process_voice_cleanup(
                    file_id,
                    enhanced_processing=enhanced_processing,
                    noise_cancelling=noise_cancelling,
                    dereverb=dereverb,
                    stem=stem,
                    splitter=splitter,
                    filter=filter_level
                )
                
                if not job_id:
                    raise Exception("Voice cleanup processing failed")
                    
            elif processing_mode == 'voice_converter':
                self.logger.info(f"Starting voice conversion for: {file_name}")
                if self.app_instance:
                    self.app_instance.log_message(f"Starting voice conversion")
                
                # Get voice converter settings from configuration
                voice_pack_id = self.app_instance.config_manager.get('voice_pack_id', 'ALEX_KAYE')
                accent_enhance = self.app_instance.config_manager.get('accent_enhance', 1.0)
                pitch_shifting = self.app_instance.config_manager.get('pitch_shifting', True)
                dereverb_enabled = self.app_instance.config_manager.get('dereverb_enabled', False)
                
                job_id = self.api_client.convert_voice(
                    file_id,
                    voice_pack_id=voice_pack_id,
                    accent_enhance=accent_enhance,
                    pitch_shifting=pitch_shifting,
                    dereverb_enabled=dereverb_enabled
                )
                
                if not job_id:
                    raise Exception("Voice conversion processing failed")
            
            else:
                raise Exception(f"Unknown processing mode: {processing_mode}")
            
            # Step 3: Wait for processing to complete
            self.logger.info(f"Waiting for processing to complete. Job ID: {job_id}")
            if self.app_instance:
                if processing_mode == 'voice_cleanup':
                    self.app_instance.log_message(f"Processing voice cleanup...")
                else:
                    self.app_instance.log_message(f"Processing voice conversion...")
            
            processed_file_url = self._wait_for_processing_completion(job_id)
            
            if not processed_file_url:
                raise Exception("Processing did not complete successfully")
            
            # Step 4: Download processed file
            if processing_mode == 'voice_cleanup':
                output_file_name = f"cleaned_{file_name}"
            else:
                output_file_name = f"converted_{file_name}"
            output_path = os.path.join(self.output_folder, output_file_name)
            
            self.logger.info(f"Downloading processed file: {output_file_name}")
            if self.app_instance:
                self.app_instance.log_message(f"Downloading processed file")
            
            success = self.api_client.download_processed_file(processed_file_url, output_path)
            
            if not success:
                raise Exception("Failed to download processed file")
            
            # Step 5: Move original file to processed folder
            processed_original_path = os.path.join(self.processed_folder, f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}")
            
            try:
                os.rename(file_path, processed_original_path)
                self.logger.info(f"Original file moved to: {processed_original_path}")
            except Exception as e:
                self.logger.warning(f"Could not move original file: {str(e)}")
            
            # Update statistics
            processing_time = time.time() - start_time
            self.stats['total_processed'] += 1
            self.stats['successful'] += 1
            self.stats['processing_time'] += processing_time
            
            # Update UI
            if self.app_instance:
                if processing_mode == 'voice_cleanup':
                    self.app_instance.log_message(f"Successfully cleaned: {file_name} (took {processing_time:.1f}s)", "success")
                else:
                    self.app_instance.log_message(f"Successfully converted: {file_name} (took {processing_time:.1f}s)", "success")
                self.app_instance.increment_files_processed()
            
            if processing_mode == 'voice_cleanup':
                self.logger.info(f"Voice cleanup completed successfully: {file_name}")
            else:
                self.logger.info(f"Voice conversion completed successfully: {file_name}")
            
        except Exception as e:
            # Update statistics
            self.stats['total_processed'] += 1
            self.stats['failed'] += 1
            
            processing_time = time.time() - start_time
            
            self.logger.error(f"File processing failed: {file_name} - {str(e)}")
            if self.app_instance:
                self.app_instance.log_message(f"Processing failed: {file_name} - {str(e)}", "error")
            
            # Don't move failed files, just log the error
        
        finally:
            # Update UI status
            if self.app_instance:
                queue_size = self.processing_queue.qsize()
                if queue_size > 0:
                    self.app_instance.update_processing_status(f"Queued ({queue_size} files)")
                else:
                    self.app_instance.update_processing_status("Idle")
    
    def _wait_for_processing_completion(self, job_id: str, timeout: int = 300) -> Optional[str]:
        """Wait for processing job to complete"""
        start_time = time.time()
        check_interval = 5  # Check every 5 seconds
        
        while time.time() - start_time < timeout:
            try:
                status, result = self.api_client.check_job_status(job_id)
                
                if status == "completed":
                    self.logger.info("Processing completed successfully")
                    return result.get('preview_url') if result else None
                
                elif status == "error":
                    self.logger.error("Processing failed with error status")
                    return None
                
                elif status == "processing":
                    self.logger.info("Processing in progress...")
                    if self.app_instance:
                        elapsed = int(time.time() - start_time)
                        self.app_instance.log_message(f"Processing... ({elapsed}s elapsed)")
                
                else:
                    self.logger.warning(f"Unknown processing status: {status}")
                
                # Wait before next check
                time.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"Error checking job status: {str(e)}")
                time.sleep(check_interval)
        
        self.logger.error(f"Processing timeout after {timeout} seconds")
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        avg_time = (self.stats['processing_time'] / self.stats['total_processed']) if self.stats['total_processed'] > 0 else 0
        
        return {
            'total_processed': self.stats['total_processed'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': (self.stats['successful'] / self.stats['total_processed'] * 100) if self.stats['total_processed'] > 0 else 0,
            'average_processing_time': avg_time,
            'queue_size': self.processing_queue.qsize(),
            'is_processing': self.is_processing
        }
    
    def clear_stats(self):
        """Clear processing statistics"""
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'processing_time': 0.0
        }
        self.logger.info("Processing statistics cleared")
