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

            # Check if multistem mode is enabled for voice_cleanup
            use_multistem = self.app_instance.config_manager.get('use_multistem', False)

            if processing_mode == 'voice_cleanup' and use_multistem:
                # Multistem processing for PostProduction
                self.logger.info(f"Starting multistem split for: {file_name}")
                if self.app_instance:
                    self.app_instance.log_message(f"Starting multistem extraction")

                # Get multistem settings
                multistem_list = self.app_instance.config_manager.get('multistem_list', ['vocals'])
                splitter = self.app_instance.config_manager.get('splitter', 'perseus')
                dereverb = self.app_instance.config_manager.get('dereverb', True)
                extraction_level = self.app_instance.config_manager.get('extraction_level', 'deep_extraction')

                job_id = self.api_client.process_multistem(
                    file_id,
                    stem_list=multistem_list,
                    splitter=splitter,
                    dereverb=dereverb,
                    extraction_level=extraction_level
                )

                if not job_id:
                    raise Exception("Multistem processing failed")

            elif processing_mode == 'voice_cleanup':
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
            self.logger.info(f"Waiting for processing to complete. File ID: {job_id}")
            if self.app_instance:
                if processing_mode == 'voice_cleanup':
                    self.app_instance.log_message(f"Processing voice cleanup...")
                else:
                    self.app_instance.log_message(f"Processing voice conversion...")
            
            processing_result = self._wait_for_processing_completion(job_id)

            if not processing_result:
                raise Exception("Processing did not complete successfully")

            # Step 4: Download processed files
            file_base, file_ext = os.path.splitext(file_name)
            downloaded_files = []

            # Check if we have multistem tracks (list of tracks)
            tracks = processing_result.get('tracks', [])

            if tracks and use_multistem and processing_mode == 'voice_cleanup':
                # Multistem mode: download each stem and the no_multistem back track
                download_no_multistem = self.app_instance.config_manager.get('download_no_multistem', True)
                multistem_list = self.app_instance.config_manager.get('multistem_list', ['vocals'])

                for track in tracks:
                    track_type = track.get('type', '')
                    track_label = track.get('label', '')
                    track_url = track.get('url', '')

                    if not track_url:
                        continue

                    # Determine output filename based on track type
                    if track_type == 'stem':
                        # Individual stem (vocals, drum, etc.)
                        stem_output_name = f"{file_base}_{track_label}{file_ext}"
                        self.logger.info(f"Downloading stem track '{track_label}': {stem_output_name}")
                        if self.app_instance:
                            self.app_instance.log_message(f"Downloading {track_label} track...")
                    elif track_type == 'back' and track_label == 'no_multistem':
                        # Background without all extracted stems
                        if not download_no_multistem:
                            continue
                        stem_output_name = f"{file_base}_back{file_ext}"
                        self.logger.info(f"Downloading no_multistem track: {stem_output_name}")
                        if self.app_instance:
                            self.app_instance.log_message("Downloading background track...")
                    else:
                        # Other back tracks (skip unless specifically requested)
                        continue

                    output_path = os.path.join(self.output_folder, stem_output_name)
                    success = self.api_client.download_processed_file(track_url, output_path)

                    if not success:
                        raise Exception(f"Failed to download track: {track_label}")

                    downloaded_files.append(output_path)

            else:
                # Legacy mode: single stem_track and back_track
                stem_track_url = processing_result.get('stem_track')
                back_track_url = processing_result.get('back_track')

                # Get user's track selection from config (default to stem_track only)
                download_stem_track = self.app_instance.config_manager.get('download_stem_track', True)
                download_back_track = self.app_instance.config_manager.get('download_back_track', False)

                # Ensure at least one track is selected
                if not download_stem_track and not download_back_track:
                    self.logger.warning("No tracks selected for download, defaulting to stem_track")
                    download_stem_track = True

                # Download stem track if selected
                if download_stem_track and stem_track_url:
                    if processing_mode == 'voice_cleanup':
                        stem_output_name = f"{file_base}_clean{file_ext}"
                    else:
                        stem_output_name = f"{file_base}_converted{file_ext}"

                    stem_output_path = os.path.join(self.output_folder, stem_output_name)

                    self.logger.info(f"Downloading stem track: {stem_output_name}")
                    if self.app_instance:
                        self.app_instance.log_message("Downloading stem track...")

                    success = self.api_client.download_processed_file(stem_track_url, stem_output_path)

                    if not success:
                        raise Exception("Failed to download stem track")

                    downloaded_files.append(stem_output_path)
                elif download_stem_track and not stem_track_url:
                    raise Exception("No download URL received for stem track")

                # Download back track if selected
                if download_back_track and back_track_url:
                    back_output_name = f"{file_base}_back{file_ext}"
                    back_output_path = os.path.join(self.output_folder, back_output_name)

                    self.logger.info(f"Downloading back track: {back_output_name}")
                    if self.app_instance:
                        self.app_instance.log_message("Downloading back track...")

                    success = self.api_client.download_processed_file(back_track_url, back_output_path)

                    if not success:
                        raise Exception("Failed to download back track")

                    downloaded_files.append(back_output_path)
                elif download_back_track and not back_track_url:
                    self.logger.warning("Back track was selected but no URL was returned")

            # If the output folder is (accidentally) the watched folder, mark the downloaded
            # files as already-processed so the FolderWatcher won't queue them again.
            try:
                if self.app_instance and getattr(self.app_instance, 'folder_watcher', None) and getattr(self.app_instance.folder_watcher, 'event_handler', None):
                    for downloaded_path in downloaded_files:
                        abs_downloaded = os.path.abspath(downloaded_path)
                        self.app_instance.folder_watcher.event_handler.processed_files.add(abs_downloaded)
            except Exception:
                # non-fatal — continue processing
                pass
            
            # Step 5: Move original file to processed folder
            processed_original_path = os.path.join(self.processed_folder, f"{datetime.now().strftime('%Y%m%d')}_{file_name}")
            
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
    
    def _wait_for_processing_completion(self, file_id: str, timeout: int = 600) -> Optional[Dict[str, Any]]:
        """Wait for processing job to complete
        
        Returns dict with stem_track and back_track URLs on success
        """
        start_time = time.time()
        check_interval = 10  # Check every 10 seconds (API recommends 15s)
        
        while time.time() - start_time < timeout:
            try:
                status, result = self.api_client.check_job_status(file_id)
                
                if status == "completed":
                    self.logger.info("Processing completed successfully")
                    if self.app_instance:
                        self.app_instance.log_message("Processing completed!")
                    return result  # Contains stem_track and back_track URLs
                
                elif status == "error":
                    error_msg = result.get('error', 'Unknown error') if result else 'Unknown error'
                    self.logger.error(f"Processing failed: {error_msg}")
                    if self.app_instance:
                        self.app_instance.log_message(f"Processing error: {error_msg}", "error")
                    return None
                
                elif status == "cancelled":
                    self.logger.warning("Processing was cancelled")
                    return None
                
                elif status == "processing":
                    progress = result.get('progress', 0) if result else 0
                    elapsed = int(time.time() - start_time)
                    self.logger.info(f"Processing in progress... {progress}%")
                    if self.app_instance:
                        self.app_instance.log_message(f"Processing... {progress}% ({elapsed}s elapsed)")
                
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
