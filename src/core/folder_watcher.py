import os
import time
import logging
import threading
from pathlib import Path
from typing import Set, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileModifiedEvent

class AudioFileHandler(FileSystemEventHandler):
    """Handles file system events for audio files"""
    
    def __init__(self, processor_callback: Callable[[str], None], supported_extensions: Set[str]):
        self.processor_callback = processor_callback
        self.supported_extensions = supported_extensions
        self.processed_files: Set[str] = set()
        self.logger = logging.getLogger(__name__)
    
    def on_created(self, event):
        """Handle file creation events"""
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def on_modified(self, event):
        """Handle file modification events"""
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def _handle_file_event(self, file_path: str):
        """Handle file events"""
        try:
            # Check if file is fully written (not still being copied)
            if not self._is_file_stable(file_path):
                return
            
            # Check if file has supported extension
            if not self._is_supported_audio_file(file_path):
                return
            
            # Check if file was already processed
            if file_path in self.processed_files:
                return
            
            # Mark as processed to avoid duplicate processing
            self.processed_files.add(file_path)
            
            self.logger.info(f"New audio file detected: {file_path}")
            
            # Call the processor callback
            self.processor_callback(file_path)
            
        except Exception as e:
            self.logger.error(f"Error handling file event for {file_path}: {str(e)}")
    
    def _is_file_stable(self, file_path: str, stability_time: float = 2.0) -> bool:
        """Check if file is stable (not being written to)"""
        try:
            # Get current file size
            current_size = os.path.getsize(file_path)
            
            # Wait a bit and check again
            time.sleep(stability_time)
            
            # If size hasn't changed, file is stable
            return os.path.getsize(file_path) == current_size
            
        except (OSError, FileNotFoundError):
            return False
    
    def _is_supported_audio_file(self, file_path: str) -> bool:
        """Check if file is a supported audio format"""
        try:
            file_extension = Path(file_path).suffix.lower().lstrip('.')
            return file_extension in self.supported_extensions
        except Exception:
            return False
    
    def reset_processed_files(self):
        """Reset the list of processed files"""
        self.processed_files.clear()

class FolderWatcher:
    """Watches a folder for new audio files"""
    
    def __init__(self, watch_folder: str, file_processor):
        self.watch_folder = watch_folder
        self.file_processor = file_processor
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[AudioFileHandler] = None
        self.is_watching = False
        self.watch_thread: Optional[threading.Thread] = None
        self.logger = logging.getLogger(__name__)
        
        # Supported audio formats (based on Lalal AI API)
        self.supported_extensions = {
            'mp3', 'wav', 'flac', 'm4a', 'ogg', 'wma', 'aac', 'aiff', 'au', 'ra', 'ram'
        }
    
    def start(self):
        """Start watching the folder"""
        try:
            if self.is_watching:
                self.logger.warning("Folder watcher is already running")
                return
            
            # Validate watch folder
            if not os.path.exists(self.watch_folder):
                raise FileNotFoundError(f"Watch folder does not exist: {self.watch_folder}")
            
            if not os.path.isdir(self.watch_folder):
                raise ValueError(f"Watch path is not a directory: {self.watch_folder}")
            
            self.logger.info(f"Starting folder watcher for: {self.watch_folder}")
            
            # Create event handler
            self.event_handler = AudioFileHandler(
                self._process_file_callback,
                self.supported_extensions
            )
            
            # Create and start observer
            self.observer = Observer()
            self.observer.schedule(
                self.event_handler,
                self.watch_folder,
                recursive=False  # Don't watch subdirectories
            )
            
            # Start observer
            self.observer.start()
            self.is_watching = True
            
            self.logger.info("Folder watcher started successfully")
            
            # Process existing files in a separate thread
            self.watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
            self.watch_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start folder watcher: {str(e)}")
            self.is_watching = False
            raise
    
    def _watch_loop(self):
        """Main watching loop that runs in a separate thread"""
        try:
            # Process existing files
            self._process_existing_files()
            
            # Keep the watcher running
            while self.is_watching:
                time.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error in watch loop: {str(e)}")
        finally:
            self.logger.info("Folder watcher loop ended")
    
    def stop(self):
        """Stop watching the folder"""
        try:
            if not self.is_watching:
                self.logger.warning("Folder watcher is not running")
                return
            
            self.logger.info("Stopping folder watcher")
            self.is_watching = False
            
            if self.observer:
                self.observer.stop()
                self.observer.join()
                self.observer = None
            
            self.event_handler = None
            self.logger.info("Folder watcher stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping folder watcher: {str(e)}")
    
    def _process_existing_files(self):
        """Process existing files in the watch folder"""
        try:
            self.logger.info("Processing existing files in watch folder")
            
            for file_name in os.listdir(self.watch_folder):
                file_path = os.path.join(self.watch_folder, file_name)
                
                # Skip directories
                if os.path.isdir(file_path):
                    continue
                
                # Check if it's a supported audio file
                if self.event_handler and self.event_handler._is_supported_audio_file(file_path):
                    # Add to processed files to avoid immediate reprocessing
                    self.event_handler.processed_files.add(file_path)
                    
                    # Process the file
                    self._process_file_callback(file_path)
            
            self.logger.info("Existing files processing completed")
            
        except Exception as e:
            self.logger.error(f"Error processing existing files: {str(e)}")
    
    def _process_file_callback(self, file_path: str):
        """Callback for processing detected files"""
        try:
            self.logger.info(f"Queuing file for processing: {file_path}")
            
            # Use the file processor to handle the file
            if self.file_processor:
                self.file_processor.process_file(file_path)
            else:
                self.logger.error("No file processor available")
                
        except Exception as e:
            self.logger.error(f"Error in file processing callback: {str(e)}")
    
    def get_status(self) -> dict:
        """Get current watcher status"""
        return {
            'is_watching': self.is_watching,
            'watch_folder': self.watch_folder,
            'supported_formats': list(self.supported_extensions),
            'processed_files_count': len(self.event_handler.processed_files) if self.event_handler else 0
        }
