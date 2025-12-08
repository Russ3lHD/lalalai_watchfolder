import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from src.api import LalalAIClient
from src.config import ConfigManager
from src.core import FolderWatcher, FileProcessor
from src.utils import (
    ShutdownManager, ThreadManager, SafeShutdownCoordinator, OperationStatus,
    LalalAICleanerError, APIError, APIAuthenticationError, APITimeoutError,
    APIRateLimitError, APIServiceUnavailableError, FileProcessingError,
    CircuitBreaker, RetryPolicy, APIClientWrapper, HealthChecker,
    FileValidator
)
from src.monitoring import HealthMonitor, ResourceManager

class LalalAIVoiceCleanerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Lalal AI Voice Cleaner")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Initialize shutdown management
        self.shutdown_manager = ShutdownManager()
        self.thread_manager = ThreadManager(self.shutdown_manager)
        self.resource_manager = ResourceManager(self.shutdown_manager)
        self.shutdown_coordinator = SafeShutdownCoordinator(
            self.shutdown_manager, self.resource_manager
        )
        
        # Initialize existing stability components
        self.file_validator = FileValidator()
        self.health_monitor = HealthMonitor()
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        self.retry_policy = RetryPolicy()
        self.health_checker = None  # Initialized after API client creation
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.api_client: Optional[LalalAIClient] = None
        self.folder_watcher: Optional[FolderWatcher] = None
        self.file_processor: Optional[FileProcessor] = None
        
        # State variables
        self.is_authenticated = False
        self.is_watching = False
        self.processing_queue = []
        
        # Setup logging
        self.setup_logging()
        
        # Register shutdown callbacks
        self.shutdown_manager.register_cleanup_callback(self._cleanup_app)
        self.shutdown_coordinator.register_pre_shutdown_callback(self._prepare_shutdown)
        
        # Create UI
        self.create_ui()
        
        # Initialize application
        self.initialize_app()
        
        # Handle window close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_format = '%(asctime)s - %(levelname)s - %(message)s'
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler('lalalai_voice_cleaner.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def create_ui(self):
        """Create the main user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Authentication Section
        self.create_auth_section(main_frame)
        
        # Folder Configuration Section
        self.create_folder_section(main_frame)
        
        # Control Section
        self.create_control_section(main_frame)
        
        # Status Section
        self.create_status_section(main_frame)
        
        # Log Section
        self.create_log_section(main_frame)
        
        # Menu
        self.create_menu()
    
    def create_auth_section(self, parent):
        """Create authentication section"""
        auth_frame = ttk.LabelFrame(parent, text="Authentication", padding="10")
        auth_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Status indicator
        self.auth_status_var = tk.StringVar(value="Not Authenticated")
        self.auth_status_label = ttk.Label(auth_frame, textvariable=self.auth_status_var)
        self.auth_status_label.grid(row=0, column=0, sticky=tk.W)
        
        # License key entry
        ttk.Label(auth_frame, text="License Key:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.license_key_var = tk.StringVar()
        self.license_entry = ttk.Entry(auth_frame, textvariable=self.license_key_var, show="*", width=40)
        self.license_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        
        # Authenticate button
        self.auth_button = ttk.Button(auth_frame, text="Authenticate", command=self.authenticate)
        self.auth_button.grid(row=1, column=2, padx=(5, 0), pady=(5, 0))
        
        # Configure auth frame column
        auth_frame.columnconfigure(1, weight=1)
    
    def create_folder_section(self, parent):
        """Create folder configuration section"""
        folder_frame = ttk.LabelFrame(parent, text="Folder Configuration", padding="10")
        folder_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Input folder
        ttk.Label(folder_frame, text="Input Folder:").grid(row=0, column=0, sticky=tk.W)
        self.input_folder_var = tk.StringVar()
        self.input_folder_entry = ttk.Entry(folder_frame, textvariable=self.input_folder_var, width=50)
        self.input_folder_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        ttk.Button(folder_frame, text="Browse", command=lambda: self.browse_folder("input")).grid(row=0, column=2, padx=(5, 0))
        
        # Output folder
        ttk.Label(folder_frame, text="Output Folder:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.output_folder_var = tk.StringVar()
        self.output_folder_entry = ttk.Entry(folder_frame, textvariable=self.output_folder_var, width=50)
        self.output_folder_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(5, 0), pady=(5, 0))
        ttk.Button(folder_frame, text="Browse", command=lambda: self.browse_folder("output")).grid(row=1, column=2, padx=(5, 0), pady=(5, 0))
        
        # Configure folder frame column
        folder_frame.columnconfigure(1, weight=1)
    
    def create_control_section(self, parent):
        """Create control buttons section"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10))
        
        # Start/Stop button
        self.start_stop_var = tk.StringVar(value="Start Watching")
        self.start_stop_button = ttk.Button(control_frame, textvariable=self.start_stop_var, command=self.toggle_watching)
        self.start_stop_button.grid(row=0, column=0, padx=(0, 10))
        
        # Settings button
        ttk.Button(control_frame, text="Settings", command=self.show_settings).grid(row=0, column=1, padx=(0, 10))
        
        # Export logs button
        ttk.Button(control_frame, text="Export Logs", command=self.export_logs).grid(row=0, column=2)
    
    def create_status_section(self, parent):
        """Create status display section"""
        status_frame = ttk.LabelFrame(parent, text="Status", padding="10")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Watching status
        self.watching_status_var = tk.StringVar(value="Inactive")
        ttk.Label(status_frame, text="Folder Watching:").grid(row=0, column=0, sticky=tk.W)
        self.watching_status_label = ttk.Label(status_frame, textvariable=self.watching_status_var, foreground="red")
        self.watching_status_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        # Processing status
        self.processing_status_var = tk.StringVar(value="Idle")
        ttk.Label(status_frame, text="Processing:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.processing_status_label = ttk.Label(status_frame, textvariable=self.processing_status_var)
        self.processing_status_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        
        # Files processed
        self.files_processed_var = tk.StringVar(value="0")
        ttk.Label(status_frame, text="Files Processed:").grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
        ttk.Label(status_frame, textvariable=self.files_processed_var).grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
    
    def create_log_section(self, parent):
        """Create log display section"""
        log_frame = ttk.LabelFrame(parent, text="Activity Log", padding="10")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Log text widget
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure log frame
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Add custom log handler
        self.log_handler = TextHandler(self.log_text)
        self.logger.addHandler(self.log_handler)
    
    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export Logs", command=self.export_logs)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def initialize_app(self):
        """Initialize application with saved settings"""
        try:
            # Load configuration
            config = self.config_manager.load_config()
            
            if config:
                # Set folder paths
                if 'input_folder' in config:
                    self.input_folder_var.set(config['input_folder'])
                if 'output_folder' in config:
                    self.output_folder_var.set(config['output_folder'])
                
                # Check if already authenticated
                if 'license_key' in config:
                    # Auto-authenticate with saved key
                    self.license_key_var.set("••••••••••••••••••••••••••••••••")
                    self.api_client = LalalAIClient(config['license_key'])
                    self.is_authenticated = True
                    self.auth_status_var.set("Authenticated ✓")
                    self.auth_status_label.config(foreground="green")
                    self.auth_button.config(state="disabled")
                    self.license_entry.config(state="readonly")
                    
                    # Initialize health checker with wrapped client
                    from retry_mechanisms import APIClientWrapper
                    wrapped_client = APIClientWrapper(self.api_client, self.retry_policy, self.circuit_breaker)
                    self.health_checker = HealthChecker(wrapped_client)
                    
                    self.log_message("Auto-authenticated with saved license key")
            
            self.log_message("Application initialized successfully")
            
        except Exception as e:
            self.log_message(f"Error initializing application: {str(e)}", "error")
    
    def authenticate(self):
        """Authenticate with Lalal AI API"""
        license_key = self.license_key_var.get().strip()
        
        if not license_key:
            messagebox.showerror("Error", "Please enter a license key")
            return
        
        try:
            self.api_client = LalalAIClient(license_key)
            
            # Test authentication
            if self.api_client.test_connection():
                self.is_authenticated = True
                self.auth_status_var.set("Authenticated ✓")
                self.auth_status_label.config(foreground="green")
                self.auth_button.config(state="disabled")
                self.license_entry.config(state="readonly")
                
                # Initialize health checker now that we have an API client
                from retry_mechanisms import APIClientWrapper
                wrapped_client = APIClientWrapper(self.api_client, self.retry_policy, self.circuit_breaker)
                self.health_checker = HealthChecker(wrapped_client)
                
                # Save license key
                self.config_manager.save_config({'license_key': license_key})
                
                self.log_message("Successfully authenticated with Lalal AI API")
            else:
                raise Exception("Invalid license key or connection failed")
                
        except Exception as e:
            self.is_authenticated = False
            self.auth_status_var.set("Authentication Failed")
            self.auth_status_label.config(foreground="red")
            messagebox.showerror("Authentication Error", str(e))
            self.log_message(f"Authentication failed: {str(e)}", "error")
    
    def browse_folder(self, folder_type):
        """Browse for folder"""
        folder = filedialog.askdirectory()
        if folder:
            if folder_type == "input":
                self.input_folder_var.set(folder)
            else:
                self.output_folder_var.set(folder)
            
            # Save configuration
            config = {
                'input_folder': self.input_folder_var.get(),
                'output_folder': self.output_folder_var.get()
            }
            self.config_manager.save_config(config)
    
    def toggle_watching(self):
        """Toggle folder watching on/off"""
        if not self.is_authenticated:
            messagebox.showerror("Error", "Please authenticate first")
            return
        
        input_folder = self.input_folder_var.get()
        output_folder = self.output_folder_var.get()
        
        if not input_folder or not output_folder:
            messagebox.showerror("Error", "Please configure input and output folders")
            return
        
        if not os.path.exists(input_folder):
            messagebox.showerror("Error", "Input folder does not exist")
            return
        
        if not os.path.exists(output_folder):
            try:
                os.makedirs(output_folder)
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create output folder: {str(e)}")
                return
        
        if self.is_watching:
            self.stop_watching()
        else:
            self.start_watching()
    
    def start_watching(self):
        """Start folder watching"""
        try:
            input_folder = self.input_folder_var.get()
            output_folder = self.output_folder_var.get()
            
            # Validate input folder using file validator
            if not self.file_validator.validate_directory(input_folder).get('is_valid', False):
                raise FileProcessingError(f"Invalid input folder: {input_folder}")
            
            # Initialize file processor with stability components
            self.file_processor = FileProcessor(
                self.api_client, 
                output_folder, 
                self,
                shutdown_coordinator=self.shutdown_coordinator
            )
            
            # Initialize folder watcher
            self.folder_watcher = FolderWatcher(input_folder, self.file_processor)
            
            # Start watching in separate thread
            self.watcher_thread = threading.Thread(target=self.folder_watcher.start, daemon=True)
            self.watcher_thread.start()
            
            self.is_watching = True
            self.start_stop_var.set("Stop Watching")
            self.watching_status_var.set("Active")
            self.watching_status_label.config(foreground="green")
            
            self.log_message(f"Started watching folder: {input_folder}")
            
        except Exception as e:
            self.log_message(f"Error starting folder watcher: {str(e)}", "error")
            messagebox.showerror("Error", f"Failed to start watching: {str(e)}")
    
    def stop_watching(self):
        """Stop folder watching"""
        try:
            if self.folder_watcher:
                self.folder_watcher.stop()
                self.folder_watcher = None
            
            self.is_watching = False
            self.start_stop_var.set("Start Watching")
            self.watching_status_var.set("Inactive")
            self.watching_status_label.config(foreground="red")
            
            self.log_message("Stopped folder watching")
            
        except Exception as e:
            self.log_message(f"Error stopping folder watcher: {str(e)}", "error")
    
    def show_settings(self):
        """Show settings dialog"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("600x700")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Settings content
        ttk.Label(settings_window, text="Application Settings", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Add settings controls here
        settings_frame = ttk.Frame(settings_window, padding="20")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Processing Mode Selection
        ttk.Label(settings_frame, text="Processing Mode:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.processing_mode_var = tk.StringVar(value=self.config_manager.get('processing_mode', 'voice_cleanup'))
        mode_combo = ttk.Combobox(settings_frame, textvariable=self.processing_mode_var, state="readonly", width=20)
        mode_combo['values'] = ('voice_cleanup', 'voice_converter')
        mode_combo.grid(row=1, column=0, sticky=tk.W, pady=(0, 20))
        
        # Voice Cleanup Settings
        ttk.Label(settings_frame, text="Voice Cleanup Options", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        
        # Enhanced Processing
        self.enhanced_processing_var = tk.BooleanVar(value=self.config_manager.get('enhanced_processing', True))
        ttk.Checkbutton(settings_frame, text="Enhanced Processing", 
                       variable=self.enhanced_processing_var).grid(row=3, column=0, sticky=tk.W, pady=2)
        
        # Noise Cancelling Level
        ttk.Label(settings_frame, text="Noise Cancelling Level:").grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        self.noise_cancelling_var = tk.IntVar(value=self.config_manager.get('noise_cancelling', 1))
        noise_frame = ttk.Frame(settings_frame)
        noise_frame.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
        ttk.Radiobutton(noise_frame, text="Mild (0)", variable=self.noise_cancelling_var, value=0).pack(side=tk.LEFT)
        ttk.Radiobutton(noise_frame, text="Normal (1)", variable=self.noise_cancelling_var, value=1).pack(side=tk.LEFT)
        ttk.Radiobutton(noise_frame, text="Aggressive (2)", variable=self.noise_cancelling_var, value=2).pack(side=tk.LEFT)
        
        # Dereverb
        self.dereverb_var = tk.BooleanVar(value=self.config_manager.get('dereverb', True))
        ttk.Checkbutton(settings_frame, text="Dereverb (Remove Echo)", 
                       variable=self.dereverb_var).grid(row=6, column=0, sticky=tk.W, pady=2)
        
        # Stem Selection
        ttk.Label(settings_frame, text="Stem to Extract:").grid(row=7, column=0, sticky=tk.W, pady=(10, 5))
        self.stem_var = tk.StringVar(value=self.config_manager.get('stem', 'voice'))
        stem_combo = ttk.Combobox(settings_frame, textvariable=self.stem_var, state="readonly", width=20)
        stem_combo['values'] = ('vocals', 'voice', 'drum', 'bass', 'piano', 'electric_guitar', 
                               'acoustic_guitar', 'synthesizer', 'strings', 'wind')
        stem_combo.grid(row=8, column=0, sticky=tk.W, pady=(0, 10))
        
        # Splitter Selection
        ttk.Label(settings_frame, text="Neural Network:").grid(row=9, column=0, sticky=tk.W, pady=(10, 5))
        self.splitter_var = tk.StringVar(value=self.config_manager.get('splitter', 'perseus'))
        splitter_combo = ttk.Combobox(settings_frame, textvariable=self.splitter_var, state="readonly", width=20)
        splitter_combo['values'] = ('auto', 'phoenix', 'orion', 'perseus')
        splitter_combo.grid(row=10, column=0, sticky=tk.W, pady=(0, 10))
        
        # Post-processing Filter
        ttk.Label(settings_frame, text="Filter Intensity:").grid(row=11, column=0, sticky=tk.W, pady=(10, 5))
        self.filter_var = tk.IntVar(value=self.config_manager.get('filter', 1))
        filter_frame = ttk.Frame(settings_frame)
        filter_frame.grid(row=12, column=0, sticky=tk.W, pady=(0, 10))
        ttk.Radiobutton(filter_frame, text="Mild (0)", variable=self.filter_var, value=0).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Normal (1)", variable=self.filter_var, value=1).pack(side=tk.LEFT)
        ttk.Radiobutton(filter_frame, text="Aggressive (2)", variable=self.filter_var, value=2).pack(side=tk.LEFT)
        
        # Voice Converter Settings
        ttk.Label(settings_frame, text="Voice Converter Options", font=("Arial", 10, "bold")).grid(row=13, column=0, sticky=tk.W, pady=(20, 10))
        
        # Voice Pack Selection
        ttk.Label(settings_frame, text="Voice Pack:").grid(row=14, column=0, sticky=tk.W, pady=(10, 5))
        self.voice_pack_var = tk.StringVar(value=self.config_manager.get('voice_pack_id', 'ALEX_KAYE'))
        voice_pack_combo = ttk.Combobox(settings_frame, textvariable=self.voice_pack_var, state="readonly", width=20)
        voice_pack_combo['values'] = ('ALEX_KAYE', 'JENNIFER', 'DAVID', 'SARAH', 'MICHAEL')  # Common voice packs
        voice_pack_combo.grid(row=15, column=0, sticky=tk.W, pady=(0, 10))
        
        # Accent Enhance
        ttk.Label(settings_frame, text="Accent Enhance:").grid(row=16, column=0, sticky=tk.W, pady=(10, 5))
        self.accent_enhance_var = tk.DoubleVar(value=self.config_manager.get('accent_enhance', 1.0))
        accent_scale = ttk.Scale(settings_frame, from_=0.5, to=2.0, variable=self.accent_enhance_var, orient=tk.HORIZONTAL)
        accent_scale.grid(row=17, column=0, sticky=tk.W+tk.E, pady=(0, 5))
        ttk.Label(settings_frame, textvariable=self.accent_enhance_var).grid(row=18, column=0, sticky=tk.W, pady=(0, 10))
        
        # Pitch Shifting
        self.pitch_shifting_var = tk.BooleanVar(value=self.config_manager.get('pitch_shifting', True))
        ttk.Checkbutton(settings_frame, text="Pitch Shifting", 
                       variable=self.pitch_shifting_var).grid(row=19, column=0, sticky=tk.W, pady=2)
        
        # Dereverb for Voice Conversion
        self.dereverb_enabled_var = tk.BooleanVar(value=self.config_manager.get('dereverb_enabled', False))
        ttk.Checkbutton(settings_frame, text="Dereverb (Voice Conversion)", 
                       variable=self.dereverb_enabled_var).grid(row=20, column=0, sticky=tk.W, pady=2)
        
        # General Settings
        ttk.Label(settings_frame, text="General Settings", font=("Arial", 10, "bold")).grid(row=21, column=0, sticky=tk.W, pady=(20, 10))
        
        # Auto-start option
        self.auto_start_var = tk.BooleanVar(value=self.config_manager.get('auto_start', False))
        ttk.Checkbutton(settings_frame, text="Auto-start watching on launch", 
                       variable=self.auto_start_var).grid(row=22, column=0, sticky=tk.W, pady=2)
        
        # Processed folder option
        self.create_processed_folder_var = tk.BooleanVar(value=self.config_manager.get('create_processed_folder', True))
        ttk.Checkbutton(settings_frame, text="Create processed subfolder", 
                       variable=self.create_processed_folder_var).grid(row=23, column=0, sticky=tk.W, pady=2)
        
        # Save button
        ttk.Button(settings_frame, text="Save Settings", 
                  command=lambda: self.save_settings(settings_window)).grid(row=24, column=0, pady=20)
    
    def save_settings(self, window):
        """Save settings and close dialog"""
        settings = {
            'auto_start': self.auto_start_var.get(),
            'create_processed_folder': self.create_processed_folder_var.get(),
            'enhanced_processing': self.enhanced_processing_var.get(),
            'noise_cancelling': self.noise_cancelling_var.get(),
            'dereverb': self.dereverb_var.get(),
            'stem': self.stem_var.get(),
            'splitter': self.splitter_var.get(),
            'filter': self.filter_var.get(),
            'processing_mode': self.processing_mode_var.get(),
            'voice_pack_id': self.voice_pack_var.get(),
            'accent_enhance': self.accent_enhance_var.get(),
            'pitch_shifting': self.pitch_shifting_var.get(),
            'dereverb_enabled': self.dereverb_enabled_var.get()
        }
        self.config_manager.save_config(settings)
        window.destroy()
        self.log_message("Settings saved")
    
    def export_logs(self):
        """Export logs to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"lalalai_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            try:
                with open('lalalai_voice_cleaner.log', 'r') as log_file:
                    logs = log_file.read()
                
                with open(filename, 'w') as export_file:
                    export_file.write(logs)
                
                messagebox.showinfo("Success", f"Logs exported to {filename}")
                self.log_message(f"Logs exported to {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {str(e)}")
                self.log_message(f"Log export failed: {str(e)}", "error")
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Lalal AI Voice Cleaner

Version 1.0.0

A desktop application for automatic voice cleanup using Lalal AI API.

Features:
• Automatic voice isolation from background music
• Folder monitoring and batch processing
• Secure credential storage
• Comprehensive logging

© 2024 Lalal AI Voice Cleaner"""
        
        messagebox.showinfo("About", about_text)
    
    def log_message(self, message: str, level: str = "info"):
        """Log message to UI and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        if level == "error":
            self.logger.error(message)
        elif level == "warning":
            self.logger.warning(message)
        else:
            self.logger.info(message)
    
    def update_processing_status(self, status: str):
        """Update processing status display"""
        self.processing_status_var.set(status)
        self.root.update_idletasks()
    
    def increment_files_processed(self):
        """Increment files processed counter"""
        current = int(self.files_processed_var.get())
        self.files_processed_var.set(str(current + 1))
        self.root.update_idletasks()
    
    def on_closing(self):
        """Handle application closing"""
        if self.is_watching:
            if messagebox.askokcancel("Quit", "Folder watching is active. Quit anyway?"):
                self.stop_watching()
            else:
                return
        
        self._on_window_close()
    
    def _on_window_close(self):
        """Handle window close event with graceful shutdown"""
        self.shutdown_coordinator.execute_shutdown()
        self.root.destroy()
    
    def _prepare_shutdown(self):
        """Prepare for shutdown"""
        self.logger.info("Preparing for shutdown...")
        
        # Stop watching if active
        if self.is_watching:
            self.stop_watching()
        
        # Cancel pending operations
        shutdown_status = self.shutdown_coordinator.get_shutdown_readiness()
        active_ops = shutdown_status['graceful_shutdown_status']['active_operations']
        
        if active_ops > 0:
            self.logger.info(f"Cancelling {active_ops} active operations...")
    
    def _cleanup_app(self):
        """Clean up application resources"""
        self.logger.info("Cleaning up application resources...")
        
        try:
            # Stop folder watcher
            if self.folder_watcher:
                self.folder_watcher.stop()
                self.logger.info("Folder watcher stopped")
            
            # Stop file processor
            if self.file_processor:
                self.file_processor.stop_processing()
                self.logger.info("File processor stopped")
            
            # Close API client
            if self.api_client:
                # Close the session if available
                if hasattr(self.api_client, 'session'):
                    self.api_client.session.close()
                self.logger.info("API client closed")
            
            self.logger.info("Application cleanup completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


class TextHandler(logging.Handler):
    """Custom logging handler to display logs in text widget"""
    
    def __init__(self, text_widget):
        logging.Handler.__init__(self)
        self.text_widget = text_widget
        self.text_widget.config(state='disabled')
    
    def emit(self, record):
        """Add log record to text widget"""
        msg = self.format(record)
        
        def append():
            self.text_widget.config(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.config(state='disabled')
            self.text_widget.see(tk.END)
        
        # Schedule the update in the main thread
        self.text_widget.after(0, append)


def main():
    """Main application entry point"""
    root = tk.Tk()
    app = LalalAIVoiceCleanerApp(root)
    
    # Handle window closing
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Start the application
    root.mainloop()


if __name__ == "__main__":
    main()