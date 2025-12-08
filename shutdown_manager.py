"""
Graceful Shutdown Manager

Provides safe application shutdown with proper resource cleanup,
thread termination, and state persistence for exe environments.
"""

import threading
import logging
import signal
import sys
import time
import atexit
from typing import List, Callable, Optional
from queue import Queue, Empty
from pathlib import Path


class ShutdownManager:
    """Manages graceful application shutdown and resource cleanup"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.shutdown_event = threading.Event()
        self.cleanup_callbacks: List[Callable[[], None]] = []
        self.is_shutting_down = False
        self.shutdown_timeout = 30  # Maximum time to wait for shutdown
        self.shutdown_lock = threading.Lock()
        
        # Register signal handlers
        self._register_signal_handlers()
        
        # Register exit handler
        atexit.register(self.emergency_cleanup)
    
    def _register_signal_handlers(self):
        """Register signal handlers for graceful shutdown"""
        try:
            # Handle Ctrl+C and termination signals
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            
            # Windows-specific: Handle console close event
            if sys.platform == 'win32':
                signal.signal(signal.SIGBREAK, self._signal_handler)
        except Exception as e:
            self.logger.warning(f"Could not register signal handlers: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.initiate_shutdown()
    
    def register_cleanup_callback(self, callback: Callable[[], None]):
        """Register a cleanup callback to be called on shutdown"""
        if callable(callback):
            self.cleanup_callbacks.append(callback)
            self.logger.debug(f"Registered cleanup callback: {callback.__name__}")
        else:
            self.logger.warning(f"Attempted to register non-callable cleanup callback")
    
    def initiate_shutdown(self):
        """Initiate graceful shutdown sequence"""
        with self.shutdown_lock:
            if self.is_shutting_down:
                self.logger.warning("Shutdown already in progress")
                return
            
            self.is_shutting_down = True
            self.shutdown_event.set()
        
        self.logger.info("Shutdown sequence initiated")
        self._execute_cleanup()
    
    def _execute_cleanup(self):
        """Execute all registered cleanup callbacks"""
        self.logger.info(f"Executing {len(self.cleanup_callbacks)} cleanup callbacks...")
        
        start_time = time.time()
        
        for callback in self.cleanup_callbacks:
            try:
                elapsed = time.time() - start_time
                remaining = self.shutdown_timeout - elapsed
                
                if remaining <= 0:
                    self.logger.warning("Shutdown timeout reached, skipping remaining callbacks")
                    break
                
                self.logger.debug(f"Executing cleanup: {callback.__name__}")
                callback()
                
            except Exception as e:
                self.logger.error(f"Error during cleanup callback {callback.__name__}: {e}")
        
        elapsed = time.time() - start_time
        self.logger.info(f"Cleanup completed in {elapsed:.2f}s")
    
    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested"""
        return self.shutdown_event.is_set()
    
    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """Wait for shutdown event"""
        return self.shutdown_event.wait(timeout)
    
    def emergency_cleanup(self):
        """Emergency cleanup called by atexit handler"""
        if not self.is_shutting_down:
            self.logger.warning("Emergency cleanup triggered - performing minimal cleanup")
            try:
                self._execute_cleanup()
            except Exception as e:
                self.logger.critical(f"Error during emergency cleanup: {e}")


class ThreadManager:
    """Manages application threads for graceful shutdown"""
    
    def __init__(self, shutdown_manager: ShutdownManager):
        self.shutdown_manager = shutdown_manager
        self.logger = logging.getLogger(__name__)
        self.managed_threads: List[threading.Thread] = []
        self.shutdown_manager.register_cleanup_callback(self.shutdown_all_threads)
    
    def register_thread(self, thread: threading.Thread):
        """Register a thread for managed shutdown"""
        if thread not in self.managed_threads:
            self.managed_threads.append(thread)
            self.logger.debug(f"Registered thread: {thread.name}")
    
    def shutdown_all_threads(self, timeout: float = 30.0):
        """Gracefully shutdown all managed threads"""
        self.logger.info(f"Shutting down {len(self.managed_threads)} managed threads...")
        
        start_time = time.time()
        active_threads = [t for t in self.managed_threads if t.is_alive()]
        
        for thread in active_threads:
            elapsed = time.time() - start_time
            remaining = timeout - elapsed
            
            if remaining <= 0:
                self.logger.warning(f"Thread shutdown timeout reached")
                break
            
            try:
                self.logger.debug(f"Waiting for thread {thread.name} to complete (timeout: {remaining:.1f}s)")
                thread.join(timeout=remaining)
                
                if thread.is_alive():
                    self.logger.warning(f"Thread {thread.name} did not complete within timeout")
                else:
                    self.logger.debug(f"Thread {thread.name} shutdown successfully")
                    
            except Exception as e:
                self.logger.error(f"Error joining thread {thread.name}: {e}")
    
    def get_active_thread_count(self) -> int:
        """Get count of active managed threads"""
        return sum(1 for t in self.managed_threads if t.is_alive())


class FileHandleManager:
    """Manages file handles for graceful cleanup"""
    
    def __init__(self, shutdown_manager: ShutdownManager):
        self.shutdown_manager = shutdown_manager
        self.logger = logging.getLogger(__name__)
        self.open_files: List[object] = []
        self.shutdown_manager.register_cleanup_callback(self.close_all_files)
    
    def register_file(self, file_handle):
        """Register a file handle for managed cleanup"""
        if file_handle not in self.open_files:
            self.open_files.append(file_handle)
            self.logger.debug(f"Registered file handle: {file_handle}")
    
    def close_all_files(self):
        """Close all registered file handles"""
        self.logger.info(f"Closing {len(self.open_files)} file handles...")
        
        for file_handle in self.open_files:
            try:
                if hasattr(file_handle, 'close') and callable(file_handle.close):
                    file_handle.close()
                    self.logger.debug(f"Closed file handle: {file_handle}")
            except Exception as e:
                self.logger.error(f"Error closing file handle {file_handle}: {e}")
        
        self.open_files.clear()


class ProcessStateManager:
    """Manages application state for recovery on restart"""
    
    def __init__(self, state_file: str = "app_state.json"):
        self.logger = logging.getLogger(__name__)
        self.state_file = Path(state_file)
        self.current_state: dict = {}
        self._load_state()
    
    def _load_state(self):
        """Load application state from file"""
        try:
            import json
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    self.current_state = json.load(f)
                self.logger.debug(f"Loaded application state: {self.current_state}")
            else:
                self.current_state = {}
        except Exception as e:
            self.logger.error(f"Error loading application state: {e}")
            self.current_state = {}
    
    def save_state(self, key: str, value: any):
        """Save a state value"""
        try:
            self.current_state[key] = value
            self._persist_state()
        except Exception as e:
            self.logger.error(f"Error saving state for key {key}: {e}")
    
    def get_state(self, key: str, default: any = None):
        """Get a state value"""
        return self.current_state.get(key, default)
    
    def _persist_state(self):
        """Persist state to file"""
        try:
            import json
            with open(self.state_file, 'w') as f:
                json.dump(self.current_state, f, indent=2, default=str)
            self.logger.debug(f"Persisted application state")
        except Exception as e:
            self.logger.error(f"Error persisting application state: {e}")
    
    def clear_state(self):
        """Clear all state"""
        self.current_state.clear()
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except Exception as e:
                self.logger.error(f"Error deleting state file: {e}")


class ShutdownPrompt:
    """Prompts user about graceful shutdown"""
    
    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def prompt_on_active_operations(self, active_operations: int) -> bool:
        """
        Prompt user if there are active operations
        
        Returns:
            True if user wants to proceed with shutdown
            False if user wants to cancel
        """
        if active_operations == 0:
            return True
        
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            root = tk.Tk()
            root.withdraw()  # Hide the window
            
            message = (
                f"There are {active_operations} active operation(s).\n\n"
                "Shutting down now may interrupt processing.\n\n"
                "Do you want to continue shutting down?"
            )
            
            result = messagebox.askyesno("Shutdown Warning", message)
            root.destroy()
            
            return result
        except Exception as e:
            self.logger.warning(f"Could not show shutdown prompt: {e}")
            return True  # Default to allowing shutdown
