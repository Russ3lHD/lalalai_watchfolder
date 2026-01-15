import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import logging
import os
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import sv_ttk

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
        
        # Configure window appearance for dark theme consistency
        self.root.configure(bg='#2b2b2b')  # Dark background color
        self.root.resizable(True, True)
        
        # Set window icon if available (optional - you can add an icon file)
        try:
            # You can add an icon by uncommenting and providing a valid icon path
            # self.root.iconbitmap('assets/icon.ico')  
            pass
        except:
            pass
        
        # Configure window border and styling hints for better dark theme integration
        self.root.attributes('-alpha', 1.0)  # Full opacity
        self.root.attributes('-topmost', False)  # Normal window stacking
        
        # Additional dark theme window styling (cross-platform)
        try:
            # Configure window transparency and border (Windows-specific)
            if sys.platform.startswith('win'):
                self.root.attributes('-toolwindow', False)  # Normal window style
        except:
            pass
        
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
        
        # Set up Sun Valley TTK theme
        sv_ttk.set_theme("dark")  # You can use "light" or "dark"
        
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
        
        # Reset button
        self.reset_button = ttk.Button(auth_frame, text="Reset", command=self.reset_license)
        self.reset_button.grid(row=1, column=3, padx=(5, 0), pady=(5, 0))
        
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
                    from src.utils.retry_mechanisms import APIClientWrapper
                    wrapped_client = APIClientWrapper(self.api_client, self.retry_policy, self.circuit_breaker)
                    self.health_checker = HealthChecker(wrapped_client)
                    
                    self.log_message("Auto-authenticated with saved license key")
            
            self.log_message("Application initialized successfully")
            
            # Auto-start watching if configured and prerequisites are met
            try:
                if config and config.get('auto_start', False):
                    input_folder = self.input_folder_var.get()
                    output_folder = self.output_folder_var.get()

                    if not self.is_authenticated:
                        self.log_message("Auto-start requested but not authenticated; not starting.")
                    elif not input_folder or not output_folder:
                        self.log_message("Auto-start requested but input/output folder not configured; not starting.")
                    elif not os.path.exists(input_folder) or not os.path.exists(output_folder):
                        self.log_message("Auto-start requested but input/output folder not found; not starting.")
                    else:
                        self.log_message("Auto-start enabled; starting folder watcher")
                        try:
                            # Start watcher; any errors are logged (do not block UI with modal dialogs during init)
                            self.start_watching()
                        except Exception as e:
                            self.log_message(f"Failed to auto-start watching: {str(e)}", "error")
            except Exception as e:
                self.logger.error(f"Error during auto-start check: {str(e)}")

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
                from src.utils.retry_mechanisms import APIClientWrapper
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
    
    def reset_license(self):
        """Reset the stored license key"""
        if messagebox.askyesno("Reset License", "Are you sure you want to reset the license key?\n\nYou will need to enter a new key to continue using the app."):
            # Clear stored license
            self.config_manager.save_config({'license_key': ''})
            
            # Reset UI state
            self.is_authenticated = False
            self.api_client = None
            self.license_key_var.set("")
            self.auth_status_var.set("Not Authenticated")
            self.auth_status_label.config(foreground="black")
            self.auth_button.config(state="normal")
            self.license_entry.config(state="normal")
            
            self.log_message("License key reset. Please enter a new key.")
    
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
        settings_window.geometry("500x800")
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Create main container with scrollbar
        main_container = ttk.Frame(settings_window)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind("<Enter>", _bind_to_mousewheel)
        canvas.bind("<Leave>", _unbind_from_mousewheel)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Settings content
        ttk.Label(scrollable_frame, text="Application Settings", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Add settings controls here
        settings_frame = ttk.Frame(scrollable_frame, padding="20")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize widget lists for conditional display
        self.voice_cleanup_widgets = []
        self.voice_converter_widgets = []
        self.general_widgets = []
        
        # Processing Mode Selection
        ttk.Label(settings_frame, text="Processing Mode:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.processing_mode_var = tk.StringVar(value=self.config_manager.get('processing_mode', 'voice_cleanup'))
        mode_combo = ttk.Combobox(settings_frame, textvariable=self.processing_mode_var, state="readonly", width=20)
        mode_combo['values'] = ('voice_cleanup',)
        mode_combo.grid(row=1, column=0, sticky=tk.W, pady=(0, 20))
        
        # Bind mode change event
        mode_combo.bind('<<ComboboxSelected>>', self.on_processing_mode_change)
        
        # Voice Cleanup Settings
        voice_cleanup_label = ttk.Label(settings_frame, text="Voice Cleanup Options", font=("Arial", 10, "bold"))
        voice_cleanup_label.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        self.voice_cleanup_widgets.append(voice_cleanup_label)
        
        # Enhanced Processing
        self.enhanced_processing_var = tk.BooleanVar(value=self.config_manager.get('enhanced_processing', True))
        enhanced_processing_check = ttk.Checkbutton(settings_frame, text="Enhanced Processing", 
                       variable=self.enhanced_processing_var)
        enhanced_processing_check.grid(row=3, column=0, sticky=tk.W, pady=2)
        self.voice_cleanup_widgets.append(enhanced_processing_check)
        
        # Noise Cancelling Level
        noise_label = ttk.Label(settings_frame, text="Noise Cancelling Level:")
        noise_label.grid(row=4, column=0, sticky=tk.W, pady=(10, 5))
        self.voice_cleanup_widgets.append(noise_label)
        
        self.noise_cancelling_var = tk.IntVar(value=self.config_manager.get('noise_cancelling', 1))
        noise_frame = ttk.Frame(settings_frame)
        noise_frame.grid(row=5, column=0, sticky=tk.W, pady=(0, 10))
        
        noise_radio1 = ttk.Radiobutton(noise_frame, text="Mild (0)", variable=self.noise_cancelling_var, value=0)
        noise_radio1.pack(side=tk.LEFT)
        noise_radio2 = ttk.Radiobutton(noise_frame, text="Normal (1)", variable=self.noise_cancelling_var, value=1)
        noise_radio2.pack(side=tk.LEFT)
        noise_radio3 = ttk.Radiobutton(noise_frame, text="Aggressive (2)", variable=self.noise_cancelling_var, value=2)
        noise_radio3.pack(side=tk.LEFT)
        
        self.voice_cleanup_widgets.extend([noise_frame, noise_radio1, noise_radio2, noise_radio3])
        
        # Dereverb
        self.dereverb_var = tk.BooleanVar(value=self.config_manager.get('dereverb', True))
        dereverb_check = ttk.Checkbutton(settings_frame, text="Dereverb (Remove Echo)", 
                       variable=self.dereverb_var)
        dereverb_check.grid(row=6, column=0, sticky=tk.W, pady=2)
        self.voice_cleanup_widgets.append(dereverb_check)
        
        # Stem Selection
        stem_label = ttk.Label(settings_frame, text="Stem to Extract:")
        stem_label.grid(row=7, column=0, sticky=tk.W, pady=(10, 5))
        self.voice_cleanup_widgets.append(stem_label)
        
        self.stem_var = tk.StringVar(value=self.config_manager.get('stem', 'voice'))
        stem_combo = ttk.Combobox(settings_frame, textvariable=self.stem_var, state="readonly", width=20)
        stem_combo['values'] = ('vocals', 'voice', 'drum', 'bass', 'piano', 'electric_guitar', 
                               'acoustic_guitar', 'synthesizer', 'strings', 'wind')
        stem_combo.grid(row=8, column=0, sticky=tk.W, pady=(0, 10))
        self.voice_cleanup_widgets.append(stem_combo)
        
        # Splitter Selection
        splitter_label = ttk.Label(settings_frame, text="Neural Network:")
        splitter_label.grid(row=9, column=0, sticky=tk.W, pady=(10, 5))
        self.voice_cleanup_widgets.append(splitter_label)
        
        self.splitter_var = tk.StringVar(value=self.config_manager.get('splitter', 'perseus'))
        splitter_combo = ttk.Combobox(settings_frame, textvariable=self.splitter_var, state="readonly", width=20)
        splitter_combo['values'] = ('auto', 'phoenix', 'orion', 'perseus', 'andromeda')
        splitter_combo.grid(row=10, column=0, sticky=tk.W, pady=(0, 10))
        self.voice_cleanup_widgets.append(splitter_combo)
        
        # Post-processing Filter
        filter_label = ttk.Label(settings_frame, text="Filter Intensity:")
        filter_label.grid(row=11, column=0, sticky=tk.W, pady=(10, 5))
        self.voice_cleanup_widgets.append(filter_label)
        
        self.filter_var = tk.IntVar(value=self.config_manager.get('filter', 1))
        filter_frame = ttk.Frame(settings_frame)
        filter_frame.grid(row=12, column=0, sticky=tk.W, pady=(0, 10))
        
        filter_radio1 = ttk.Radiobutton(filter_frame, text="Mild (0)", variable=self.filter_var, value=0)
        filter_radio1.pack(side=tk.LEFT)
        filter_radio2 = ttk.Radiobutton(filter_frame, text="Normal (1)", variable=self.filter_var, value=1)
        filter_radio2.pack(side=tk.LEFT)
        filter_radio3 = ttk.Radiobutton(filter_frame, text="Aggressive (2)", variable=self.filter_var, value=2)
        filter_radio3.pack(side=tk.LEFT)
        
        self.voice_cleanup_widgets.extend([filter_frame, filter_radio1, filter_radio2, filter_radio3])
        
        # Voice Converter Settings
        voice_converter_label = ttk.Label(settings_frame, text="Voice Converter Options", font=("Arial", 10, "bold"))
        voice_converter_label.grid(row=13, column=0, sticky=tk.W, pady=(20, 10))
        self.voice_converter_widgets.append(voice_converter_label)
        
        # General Settings
        general_label = ttk.Label(settings_frame, text="General Settings", font=("Arial", 10, "bold"))
        general_label.grid(row=21, column=0, sticky=tk.W, pady=(20, 10))
        self.general_widgets.append(general_label)
        
        # Auto-start option
        self.auto_start_var = tk.BooleanVar(value=self.config_manager.get('auto_start', False))
        auto_start_check = ttk.Checkbutton(settings_frame, text="Auto-start watching on launch", 
                       variable=self.auto_start_var)
        auto_start_check.grid(row=22, column=0, sticky=tk.W, pady=2)
        self.general_widgets.append(auto_start_check)
        
        # Processed folder option
        self.create_processed_folder_var = tk.BooleanVar(value=self.config_manager.get('create_processed_folder', True))
        processed_folder_check = ttk.Checkbutton(settings_frame, text="Create processed subfolder", 
                       variable=self.create_processed_folder_var)
        processed_folder_check.grid(row=23, column=0, sticky=tk.W, pady=2)
        self.general_widgets.append(processed_folder_check)
        
        # Performance Settings
        performance_label = ttk.Label(settings_frame, text="Performance Settings", font=("Arial", 10, "bold"))
        performance_label.grid(row=24, column=0, sticky=tk.W, pady=(20, 10))
        self.general_widgets.append(performance_label)
        
        # Max Queue Size
        max_queue_label = ttk.Label(settings_frame, text="Max Queue Size:")
        max_queue_label.grid(row=25, column=0, sticky=tk.W, pady=(10, 5))
        self.general_widgets.append(max_queue_label)
        
        self.max_queue_size_var = tk.IntVar(value=self.config_manager.get('max_queue_size', 100))
        max_queue_frame = ttk.Frame(settings_frame)
        max_queue_frame.grid(row=26, column=0, sticky=tk.W, pady=(0, 10))
        max_queue_spin = ttk.Spinbox(max_queue_frame, from_=1, to=1000, textvariable=self.max_queue_size_var, width=10)
        max_queue_spin.pack(side=tk.LEFT)
        max_queue_range_label = ttk.Label(max_queue_frame, text="(1-1000)", font=("Arial", 8))
        max_queue_range_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.general_widgets.extend([max_queue_frame, max_queue_spin, max_queue_range_label])
        
        # Retry Attempts
        retry_label = ttk.Label(settings_frame, text="Retry Attempts:")
        retry_label.grid(row=27, column=0, sticky=tk.W, pady=(10, 5))
        self.general_widgets.append(retry_label)
        
        self.retry_attempts_var = tk.IntVar(value=self.config_manager.get('retry_attempts', 3))
        retry_frame = ttk.Frame(settings_frame)
        retry_frame.grid(row=28, column=0, sticky=tk.W, pady=(0, 10))
        retry_spin = ttk.Spinbox(retry_frame, from_=1, to=10, textvariable=self.retry_attempts_var, width=10)
        retry_spin.pack(side=tk.LEFT)
        retry_range_label = ttk.Label(retry_frame, text="(1-10)", font=("Arial", 8))
        retry_range_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.general_widgets.extend([retry_frame, retry_spin, retry_range_label])
        
        # Timeout Seconds
        timeout_label = ttk.Label(settings_frame, text="Timeout (seconds):")
        timeout_label.grid(row=29, column=0, sticky=tk.W, pady=(10, 5))
        self.general_widgets.append(timeout_label)
        
        self.timeout_seconds_var = tk.IntVar(value=self.config_manager.get('timeout_seconds', 300))
        timeout_frame = ttk.Frame(settings_frame)
        timeout_frame.grid(row=30, column=0, sticky=tk.W, pady=(0, 10))
        timeout_spin = ttk.Spinbox(timeout_frame, from_=30, to=3600, increment=30, textvariable=self.timeout_seconds_var, width=10)
        timeout_spin.pack(side=tk.LEFT)
        timeout_range_label = ttk.Label(timeout_frame, text="(30-3600)", font=("Arial", 8))
        timeout_range_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.general_widgets.extend([timeout_frame, timeout_spin, timeout_range_label])
        
        # Health Check Interval
        health_label = ttk.Label(settings_frame, text="Health Check Interval:")
        health_label.grid(row=31, column=0, sticky=tk.W, pady=(10, 5))
        self.general_widgets.append(health_label)
        
        self.health_check_interval_var = tk.IntVar(value=self.config_manager.get('health_check_interval', 30))
        health_frame = ttk.Frame(settings_frame)
        health_frame.grid(row=32, column=0, sticky=tk.W, pady=(0, 10))
        health_spin = ttk.Spinbox(health_frame, from_=5, to=300, increment=5, textvariable=self.health_check_interval_var, width=10)
        health_spin.pack(side=tk.LEFT)
        health_range_label = ttk.Label(health_frame, text="seconds (5-300)", font=("Arial", 8))
        health_range_label.pack(side=tk.LEFT, padx=(5, 0))
        
        self.general_widgets.extend([health_frame, health_spin, health_range_label])
        
        # Save button
        save_button = ttk.Button(settings_frame, text="Save Settings", 
                  command=lambda: self.save_settings(settings_window))
        save_button.grid(row=33, column=0, pady=20)
        self.general_widgets.append(save_button)
        
        # Initialize mode-specific visibility
        self.root.update_idletasks()  # Ensure UI is fully rendered
        self.on_processing_mode_change()
        
        # Ensure general settings are always visible
        self._show_widgets(self.general_widgets, True)
    
    def on_processing_mode_change(self, event=None):
        """Handle processing mode change to show/hide relevant settings"""
        mode = self.processing_mode_var.get()
        
        if mode == 'voice_cleanup':
            # Show voice cleanup settings, hide voice converter settings
            self._show_widgets(self.voice_cleanup_widgets, True)
            self._show_widgets(self.voice_converter_widgets, False)
        else:  # voice_converter
            # Show voice converter settings, hide voice cleanup settings
            self._show_widgets(self.voice_cleanup_widgets, False)
            self._show_widgets(self.voice_converter_widgets, True)
    
    def _show_widgets(self, widgets, show):
        """Show or hide a list of widgets"""
        for widget in widgets:
            try:
                if show:
                    widget.grid()
                else:
                    widget.grid_remove()
            except Exception as e:
                # Skip widgets that might not have grid method
                pass
        
        # Also update the canvas scrollregion after showing/hiding widgets
        self.root.update_idletasks()
    
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
            'max_queue_size': self.max_queue_size_var.get(),
            'retry_attempts': self.retry_attempts_var.get(),
            'timeout_seconds': self.timeout_seconds_var.get(),
            'health_check_interval': self.health_check_interval_var.get()
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
        about_text = """Lalal AI Watchfolder

Version 1.5

A desktop application for automatic voice cleanup using Lalal AI API.

Features:
• Automatic voice isolation from background audio
• Folder monitoring and batch processing
• Secure credential storage
• Comprehensive logging

2025 Lalal AI Watchfolder"""
        
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