"""
Resource Monitor

Monitors and controls resource usage (temp files, process resources)
for exe environments with automatic cleanup and limits.
"""

import os
import shutil
import tempfile
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import psutil


@dataclass
class ResourceInfo:
    """Resource usage information"""
    temp_files_count: int
    temp_files_size_mb: float
    temp_dirs_count: int
    process_memory_mb: float
    process_cpu_percent: float
    disk_free_gb: float
    disk_usage_percent: float
    active_threads: int


class TempFileManager:
    """Manages temporary files and directories"""
    
    def __init__(self, base_temp_dir: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.base_temp_dir = Path(base_temp_dir) if base_temp_dir else Path(tempfile.gettempdir()) / "lalalai_cleaner"
        self.tracked_temps: List[Path] = []
        self.max_temp_size_mb = 500  # Maximum total temp size
        self.temp_retention_hours = 24  # Delete temps older than this
        
        # Create base temp directory
        self.base_temp_dir.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Temp manager initialized: {self.base_temp_dir}")
    
    def create_temp_file(self, prefix: str = "lalalai_", suffix: str = ".tmp") -> Path:
        """Create a temporary file and track it"""
        try:
            temp_file = Path(tempfile.mktemp(prefix=prefix, suffix=suffix, dir=str(self.base_temp_dir)))
            temp_file.touch()
            self.tracked_temps.append(temp_file)
            self.logger.debug(f"Created temp file: {temp_file}")
            
            # Check if cleanup is needed
            self._cleanup_if_needed()
            
            return temp_file
        except Exception as e:
            self.logger.error(f"Error creating temp file: {e}")
            raise
    
    def create_temp_dir(self, prefix: str = "lalalai_") -> Path:
        """Create a temporary directory and track it"""
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix=prefix, dir=str(self.base_temp_dir)))
            self.tracked_temps.append(temp_dir)
            self.logger.debug(f"Created temp directory: {temp_dir}")
            
            # Check if cleanup is needed
            self._cleanup_if_needed()
            
            return temp_dir
        except Exception as e:
            self.logger.error(f"Error creating temp directory: {e}")
            raise
    
    def cleanup_temp(self, path: Path) -> bool:
        """Clean up a specific temp file/directory"""
        try:
            if not path.exists():
                self.logger.warning(f"Temp path does not exist: {path}")
                return False
            
            if path.is_dir():
                shutil.rmtree(path)
                self.logger.debug(f"Removed temp directory: {path}")
            else:
                path.unlink()
                self.logger.debug(f"Removed temp file: {path}")
            
            if path in self.tracked_temps:
                self.tracked_temps.remove(path)
            
            return True
        except Exception as e:
            self.logger.error(f"Error cleaning up temp {path}: {e}")
            return False
    
    def cleanup_all_temps(self):
        """Clean up all tracked temporary files and directories"""
        self.logger.info(f"Cleaning up {len(self.tracked_temps)} temporary items...")
        
        for temp_path in self.tracked_temps[:]:
            self.cleanup_temp(temp_path)
        
        self.logger.info("Temporary cleanup completed")
    
    def cleanup_old_temps(self, hours: Optional[int] = None):
        """Clean up temporary files older than specified hours"""
        hours = hours or self.temp_retention_hours
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        self.logger.info(f"Cleaning up temps older than {hours} hours...")
        
        if not self.base_temp_dir.exists():
            return
        
        for temp_path in self.base_temp_dir.iterdir():
            try:
                mtime = datetime.fromtimestamp(temp_path.stat().st_mtime)
                if mtime < cutoff_time:
                    self.cleanup_temp(temp_path)
            except Exception as e:
                self.logger.warning(f"Error checking temp age {temp_path}: {e}")
    
    def _cleanup_if_needed(self):
        """Check total temp size and cleanup if needed"""
        try:
            total_size_mb = self._get_total_temp_size_mb()
            
            if total_size_mb > self.max_temp_size_mb:
                self.logger.warning(f"Temp size ({total_size_mb:.1f}MB) exceeds limit ({self.max_temp_size_mb}MB)")
                self.cleanup_old_temps(hours=1)  # Clean temps older than 1 hour
        except Exception as e:
            self.logger.warning(f"Error checking temp size: {e}")
    
    def _get_total_temp_size_mb(self) -> float:
        """Get total size of all tracked temps"""
        total_size = 0
        
        for temp_path in self.tracked_temps:
            try:
                if temp_path.is_dir():
                    total_size += sum(
                        f.stat().st_size for f in temp_path.rglob('*') if f.is_file()
                    )
                elif temp_path.is_file():
                    total_size += temp_path.stat().st_size
            except Exception as e:
                self.logger.debug(f"Error calculating size for {temp_path}: {e}")
        
        return total_size / (1024 * 1024)  # Convert to MB
    
    def get_temp_stats(self) -> Dict[str, Any]:
        """Get statistics about temporary files"""
        return {
            'tracked_count': len(self.tracked_temps),
            'total_size_mb': self._get_total_temp_size_mb(),
            'temp_dir': str(self.base_temp_dir)
        }


class ProcessResourceMonitor:
    """Monitors process resource usage"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.process = psutil.Process()
        self.max_memory_mb = 500  # Alert if process exceeds this
        self.memory_warning_threshold = 0.85  # 85% of max
    
    def get_resource_info(self) -> ResourceInfo:
        """Get current resource information"""
        try:
            process_memory = self.process.memory_info().rss / (1024 * 1024)
            process_cpu = self.process.cpu_percent(interval=0.1)
            
            disk_usage = shutil.disk_usage('/')
            disk_free_gb = disk_usage.free / (1024**3)
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            active_threads = threading.active_count() if 'threading' in globals() else 0
            
            return ResourceInfo(
                temp_files_count=0,
                temp_files_size_mb=0.0,
                temp_dirs_count=0,
                process_memory_mb=process_memory,
                process_cpu_percent=process_cpu,
                disk_free_gb=disk_free_gb,
                disk_usage_percent=disk_percent,
                active_threads=active_threads
            )
        except Exception as e:
            self.logger.error(f"Error getting resource info: {e}")
            raise
    
    def check_resource_limits(self) -> List[str]:
        """Check if resource limits are exceeded"""
        warnings = []
        
        try:
            info = self.get_resource_info()
            
            if info.process_memory_mb > self.max_memory_mb:
                warnings.append(
                    f"Process memory usage ({info.process_memory_mb:.1f}MB) exceeds limit ({self.max_memory_mb}MB)"
                )
            
            if info.process_memory_mb > self.max_memory_mb * self.memory_warning_threshold:
                warnings.append(
                    f"Process memory usage ({info.process_memory_mb:.1f}MB) approaching limit"
                )
            
            if info.disk_free_gb < 1:
                warnings.append(f"Low disk space: {info.disk_free_gb:.2f}GB free")
            
            if info.disk_usage_percent > 95:
                warnings.append(f"Disk almost full: {info.disk_usage_percent:.1f}% used")
            
            return warnings
        except Exception as e:
            self.logger.error(f"Error checking resource limits: {e}")
            return []


class ResourceManager:
    """Central resource management coordinator"""
    
    def __init__(self, shutdown_manager=None):
        self.logger = logging.getLogger(__name__)
        self.temp_manager = TempFileManager()
        self.process_monitor = ProcessResourceMonitor()
        self.shutdown_manager = shutdown_manager
        
        # Register cleanup with shutdown manager if provided
        if shutdown_manager:
            shutdown_manager.register_cleanup_callback(self.cleanup_all_resources)
    
    def cleanup_all_resources(self):
        """Clean up all resources"""
        self.logger.info("Cleaning up all resources...")
        
        try:
            self.temp_manager.cleanup_all_temps()
            self.logger.info("Resources cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during resource cleanup: {e}")
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get comprehensive resource status"""
        try:
            warnings = self.process_monitor.check_resource_limits()
            resource_info = self.process_monitor.get_resource_info()
            temp_stats = self.temp_manager.get_temp_stats()
            
            return {
                'resource_info': resource_info,
                'temp_stats': temp_stats,
                'warnings': warnings,
                'healthy': len(warnings) == 0
            }
        except Exception as e:
            self.logger.error(f"Error getting resource status: {e}")
            return {
                'resource_info': None,
                'temp_stats': None,
                'warnings': [str(e)],
                'healthy': False
            }
    
    def enforce_resource_limits(self):
        """Enforce resource limits by cleaning up if necessary"""
        warnings = self.process_monitor.check_resource_limits()
        
        for warning in warnings:
            self.logger.warning(f"Resource limit: {warning}")
        
        if warnings:
            # Clean up old temps if there are resource warnings
            self.temp_manager.cleanup_old_temps(hours=6)


# Import threading for active_count
import threading
