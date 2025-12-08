"""
Health monitoring system for comprehensive application diagnostics
Provides system health checks, performance monitoring, and diagnostics
"""

import os
import sys
import time
import psutil
import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import json


@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: float
    threshold: float
    status: str  # 'healthy', 'warning', 'critical'
    unit: str
    description: str
    timestamp: float


@dataclass
class SystemHealth:
    """Overall system health status"""
    overall_status: str  # 'healthy', 'degraded', 'critical', 'error'
    timestamp: float
    metrics: List[HealthMetric]
    uptime: float
    memory_usage: float
    cpu_usage: float
    disk_usage: float
    active_threads: int
    error_count: int
    warnings: List[str]


class HealthMonitor:
    """
    Comprehensive health monitoring system
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or self._default_config()
        self.logger = logging.getLogger(__name__)
        
        # Monitoring state
        self.is_monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.metrics_history: List[SystemHealth] = []
        self.max_history_size = 1000
        
        # Health thresholds
        self.thresholds = {
            'cpu_critical': 90.0,
            'cpu_warning': 75.0,
            'memory_critical': 90.0,
            'memory_warning': 75.0,
            'disk_critical': 95.0,
            'disk_warning': 85.0,
            'thread_critical': 100,
            'thread_warning': 50,
            'error_rate_critical': 10.0,  # errors per minute
            'error_rate_warning': 5.0
        }
        
        # Callbacks for health events
        self.health_callbacks: List[Callable] = []
        
        # Performance tracking
        self.start_time = time.time()
        self.error_counts: Dict[str, int] = {}
        self.last_health_check = 0
        
        self.logger.info("Health monitor initialized")
    
    def _default_config(self) -> Dict[str, Any]:
        """Default health monitor configuration"""
        return {
            'monitoring_interval': 30,  # seconds
            'enable_performance_monitoring': True,
            'enable_system_monitoring': True,
            'enable_disk_monitoring': True,
            'enable_memory_monitoring': True,
            'enable_cpu_monitoring': True,
            'log_health_events': True,
            'max_metrics_history': 1000,
            'alert_on_critical': True,
            'alert_on_warning': False
        }
    
    def start_monitoring(self):
        """Start health monitoring"""
        if self.is_monitoring:
            self.logger.warning("Health monitoring is already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Health monitoring stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                health_status = self.check_system_health()
                self._process_health_status(health_status)
                time.sleep(self.config['monitoring_interval'])
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {str(e)}")
                time.sleep(5)  # Brief pause before retrying
    
    def check_system_health(self) -> SystemHealth:
        """Perform comprehensive system health check"""
        metrics = []
        warnings = []
        
        try:
            # System metrics
            if self.config['enable_system_monitoring']:
                metrics.extend(self._get_system_metrics())
            
            # Performance metrics
            if self.config['enable_performance_monitoring']:
                metrics.extend(self._get_performance_metrics())
            
            # Memory metrics
            if self.config['enable_memory_monitoring']:
                metrics.extend(self._get_memory_metrics())
            
            # CPU metrics
            if self.config['enable_cpu_monitoring']:
                metrics.extend(self._get_cpu_metrics())
            
            # Disk metrics
            if self.config['enable_disk_monitoring']:
                metrics.extend(self._get_disk_metrics())
            
            # Determine overall status
            overall_status = self._determine_overall_status(metrics)
            
            # Create health status
            health_status = SystemHealth(
                overall_status=overall_status,
                timestamp=time.time(),
                metrics=metrics,
                uptime=time.time() - self.start_time,
                memory_usage=self._get_memory_usage(),
                cpu_usage=self._get_cpu_usage(),
                disk_usage=self._get_disk_usage(),
                active_threads=threading.active_count(),
                error_count=sum(self.error_counts.values()),
                warnings=warnings
            )
            
            self.last_health_check = time.time()
            return health_status
            
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return SystemHealth(
                overall_status='error',
                timestamp=time.time(),
                metrics=[],
                uptime=time.time() - self.start_time,
                memory_usage=0,
                cpu_usage=0,
                disk_usage=0,
                active_threads=threading.active_count(),
                error_count=sum(self.error_counts.values()),
                warnings=[f"Health check error: {str(e)}"]
            )
    
    def _get_system_metrics(self) -> List[HealthMetric]:
        """Get system-level metrics"""
        metrics = []
        
        try:
            # System load average (Unix-like systems)
            if hasattr(os, 'getloadavg'):
                load_avg = os.getloadavg()[0]  # 1-minute load average
                cpu_count = psutil.cpu_count()
                
                load_percentage = (load_avg / cpu_count) * 100 if cpu_count > 0 else 0
                
                metrics.append(HealthMetric(
                    name='system_load',
                    value=load_percentage,
                    threshold=self.thresholds['cpu_warning'],
                    status='warning' if load_percentage > self.thresholds['cpu_warning'] else 'healthy',
                    unit='%',
                    description='System load average percentage'
                ))
        
        except Exception as e:
            self.logger.error(f"Failed to get system metrics: {str(e)}")
        
        return metrics
    
    def _get_performance_metrics(self) -> List[HealthMetric]:
        """Get performance-related metrics"""
        metrics = []
        
        try:
            # Process information
            process = psutil.Process()
            
            # CPU time
            cpu_time = process.cpu_times()
            total_cpu_time = cpu_time.user + cpu_time.system
            
            metrics.append(HealthMetric(
                name='process_cpu_time',
                value=total_cpu_time,
                threshold=0,  # No specific threshold
                status='healthy',
                unit='seconds',
                description='Total CPU time used by process'
            ))
            
            # File descriptors (Unix-like systems)
            if hasattr(process, 'num_fds'):
                fd_count = process.num_fds()
                metrics.append(HealthMetric(
                    name='file_descriptors',
                    value=fd_count,
                    threshold=self.thresholds['thread_warning'],
                    status='warning' if fd_count > self.thresholds['thread_warning'] else 'healthy',
                    unit='count',
                    description='Number of open file descriptors'
                ))
        
        except Exception as e:
            self.logger.error(f"Failed to get performance metrics: {str(e)}")
        
        return metrics
    
    def _get_memory_metrics(self) -> List[HealthMetric]:
        """Get memory-related metrics"""
        metrics = []
        
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_percent = process.memory_percent()
            
            # RSS (Resident Set Size)
            metrics.append(HealthMetric(
                name='memory_rss',
                value=memory_info.rss,
                threshold=self._get_memory_threshold(),
                status='critical' if memory_percent > self.thresholds['memory_critical'] 
                       else 'warning' if memory_percent > self.thresholds['memory_warning'] 
                       else 'healthy',
                unit='bytes',
                description='Resident Set Size memory usage'
            ))
            
            # Virtual memory
            metrics.append(HealthMetric(
                name='memory_virtual',
                value=memory_info.vms,
                threshold=0,  # No specific threshold
                status='healthy',
                unit='bytes',
                description='Virtual memory usage'
            ))
            
            # Memory percentage
            metrics.append(HealthMetric(
                name='memory_percent',
                value=memory_percent,
                threshold=self.thresholds['memory_warning'],
                status='critical' if memory_percent > self.thresholds['memory_critical'] 
                       else 'warning' if memory_percent > self.thresholds['memory_warning'] 
                       else 'healthy',
                unit='%',
                description='Memory usage percentage'
            ))
        
        except Exception as e:
            self.logger.error(f"Failed to get memory metrics: {str(e)}")
        
        return metrics
    
    def _get_cpu_metrics(self) -> List[HealthMetric]:
        """Get CPU-related metrics"""
        metrics = []
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            metrics.append(HealthMetric(
                name='cpu_percent',
                value=cpu_percent,
                threshold=self.thresholds['cpu_warning'],
                status='critical' if cpu_percent > self.thresholds['cpu_critical'] 
                       else 'warning' if cpu_percent > self.thresholds['cpu_warning'] 
                       else 'healthy',
                unit='%',
                description='CPU usage percentage'
            ))
            
            # CPU count
            cpu_count = psutil.cpu_count()
            metrics.append(HealthMetric(
                name='cpu_count',
                value=cpu_count,
                threshold=0,
                status='healthy',
                unit='count',
                description='Number of CPU cores'
            ))
        
        except Exception as e:
            self.logger.error(f"Failed to get CPU metrics: {str(e)}")
        
        return metrics
    
    def _get_disk_metrics(self) -> List[HealthMetric]:
        """Get disk-related metrics"""
        metrics = []
        
        try:
            # Check disk usage for current directory
            disk_usage = psutil.disk_usage('.')
            disk_percent = (disk_usage.used / disk_usage.total) * 100
            
            metrics.append(HealthMetric(
                name='disk_percent',
                value=disk_percent,
                threshold=self.thresholds['disk_warning'],
                status='critical' if disk_percent > self.thresholds['disk_critical'] 
                       else 'warning' if disk_percent > self.thresholds['disk_warning'] 
                       else 'healthy',
                unit='%',
                description='Disk usage percentage'
            ))
            
            # Free space
            metrics.append(HealthMetric(
                name='disk_free',
                value=disk_usage.free,
                threshold=1024**3,  # 1GB threshold
                status='warning' if disk_usage.free < 1024**3 else 'healthy',
                unit='bytes',
                description='Free disk space'
            ))
        
        except Exception as e:
            self.logger.error(f"Failed to get disk metrics: {str(e)}")
        
        return metrics
    
    def _determine_overall_status(self, metrics: List[HealthMetric]) -> str:
        """Determine overall health status from metrics"""
        if not metrics:
            return 'healthy'
        
        critical_count = sum(1 for m in metrics if m.status == 'critical')
        warning_count = sum(1 for m in metrics if m.status == 'warning')
        
        if critical_count > 0:
            return 'critical'
        elif warning_count > 0:
            return 'degraded'
        else:
            return 'healthy'
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage percentage"""
        try:
            return psutil.Process().memory_percent()
        except:
            return 0.0
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0
    
    def _get_disk_usage(self) -> float:
        """Get current disk usage percentage"""
        try:
            disk_usage = psutil.disk_usage('.')
            return (disk_usage.used / disk_usage.total) * 100
        except:
            return 0.0
    
    def _get_memory_threshold(self) -> int:
        """Get memory threshold in bytes"""
        try:
            memory = psutil.virtual_memory()
            warning_bytes = memory.total * (self.thresholds['memory_warning'] / 100)
            return int(warning_bytes)
        except:
            return 0
    
    def _process_health_status(self, health_status: SystemHealth):
        """Process and handle health status updates"""
        # Add to history
        self.metrics_history.append(health_status)
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history.pop(0)
        
        # Trigger callbacks
        for callback in self.health_callbacks:
            try:
                callback(health_status)
            except Exception as e:
                self.logger.error(f"Health callback failed: {str(e)}")
        
        # Log health events
        if self.config['log_health_events']:
            self._log_health_event(health_status)
        
        # Send alerts
        if health_status.overall_status == 'critical' and self.config['alert_on_critical']:
            self._send_alert('CRITICAL', health_status)
        elif health_status.overall_status == 'degraded' and self.config['alert_on_warning']:
            self._send_alert('WARNING', health_status)
    
    def _log_health_event(self, health_status: SystemHealth):
        """Log health status changes"""
        if not hasattr(self, '_last_status'):
            self._last_status = 'unknown'
        
        if health_status.overall_status != self._last_status:
            if health_status.overall_status == 'critical':
                self.logger.critical(f"System health degraded to CRITICAL: {health_status.overall_status}")
            elif health_status.overall_status == 'degraded':
                self.logger.warning(f"System health degraded to DEGRADED: {health_status.overall_status}")
            elif health_status.overall_status == 'healthy':
                self.logger.info(f"System health recovered to HEALTHY")
            
            self._last_status = health_status.overall_status
    
    def _send_alert(self, level: str, health_status: SystemHealth):
        """Send health alert"""
        self.logger.warning(f"HEALTH ALERT [{level}]: System status is {health_status.overall_status}")
        
        # Add implementation for actual alerting (email, webhook, etc.)
        # For now, just log the alert
    
    def add_health_callback(self, callback: Callable[[SystemHealth], None]):
        """Add callback for health status changes"""
        self.health_callbacks.append(callback)
    
    def record_error(self, error_type: str):
        """Record an error occurrence"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get current health status"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None
    
    def get_health_history(self, duration_minutes: int = 60) -> List[SystemHealth]:
        """Get health history for specified duration"""
        cutoff_time = time.time() - (duration_minutes * 60)
        return [h for h in self.metrics_history if h.timestamp >= cutoff_time]
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary statistics"""
        current_health = self.get_current_health()
        if not current_health:
            return {'status': 'unknown', 'message': 'No health data available'}
        
        history = self.get_health_history(60)  # Last hour
        
        summary = {
            'current_status': current_health.overall_status,
            'uptime_hours': current_health.uptime / 3600,
            'memory_usage': current_health.memory_usage,
            'cpu_usage': current_health.cpu_usage,
            'disk_usage': current_health.disk_usage,
            'active_threads': current_health.active_threads,
            'total_errors': current_health.error_count,
            'metrics_count': len(current_health.metrics),
            'history_points': len(history),
            'timestamp': current_health.timestamp
        }
        
        # Calculate health trend
        if len(history) > 1:
            recent_statuses = [h.overall_status for h in history[-10:]]  # Last 10 checks
            if recent_statuses.count('critical') > 5:
                summary['trend'] = 'declining'
            elif recent_statuses.count('healthy') > 5:
                summary['trend'] = 'stable'
            else:
                summary['trend'] = 'fluctuating'
        else:
            summary['trend'] = 'unknown'
        
        return summary
    
    def export_health_data(self, file_path: str, duration_hours: int = 24) -> bool:
        """Export health data to JSON file"""
        try:
            cutoff_time = time.time() - (duration_hours * 3600)
            history = [h for h in self.metrics_history if h.timestamp >= cutoff_time]
            
            export_data = {
                'export_timestamp': time.time(),
                'duration_hours': duration_hours,
                'summary': self.get_health_summary(),
                'history': [asdict(h) for h in history]
            }
            
            with open(file_path, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            
            self.logger.info(f"Health data exported to {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to export health data: {str(e)}")
            return False


class ApplicationDiagnostics:
    """
    Application-specific diagnostics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def diagnose_application(self) -> Dict[str, Any]:
        """Perform application-specific diagnostics"""
        diagnostics = {
            'timestamp': time.time(),
            'python_version': sys.version,
            'platform': sys.platform,
            'executable': sys.executable,
            'environment_variables': self._get_relevant_env_vars(),
            'file_permissions': self._check_file_permissions(),
            'dependencies': self._check_dependencies(),
            'network_connectivity': self._check_network_connectivity()
        }
        
        return diagnostics
    
    def _get_relevant_env_vars(self) -> Dict[str, str]:
        """Get relevant environment variables"""
        relevant_vars = [
            'PATH', 'PYTHONPATH', 'HOME', 'USER', 'LANG', 'TZ'
        ]
        return {var: os.environ.get(var, 'not set') for var in relevant_vars}
    
    def _check_file_permissions(self) -> Dict[str, bool]:
        """Check file permissions for critical paths"""
        critical_paths = ['.', os.path.expanduser('~'), '/tmp']
        permissions = {}
        
        for path in critical_paths:
            try:
                permissions[path] = {
                    'readable': os.access(path, os.R_OK),
                    'writable': os.access(path, os.W_OK),
                    'exists': os.path.exists(path)
                }
            except Exception as e:
                permissions[path] = {'error': str(e)}
        
        return permissions
    
    def _check_dependencies(self) -> Dict[str, bool]:
        """Check if critical dependencies are available"""
        dependencies = [
            'requests', 'cryptography', 'watchdog', 'PIL', 'tkinter'
        ]
        
        dependency_status = {}
        for dep in dependencies:
            try:
                if dep == 'PIL':
                    import PIL
                    dependency_status[dep] = True
                elif dep == 'tkinter':
                    import tkinter
                    dependency_status[dep] = True
                else:
                    __import__(dep)
                    dependency_status[dep] = True
            except ImportError:
                dependency_status[dep] = False
        
        return dependency_status
    
    def _check_network_connectivity(self) -> Dict[str, bool]:
        """Check network connectivity to important services"""
        services = [
            'https://www.google.com',
            'https://www.lalal.ai'
        ]
        
        connectivity = {}
        import requests
        
        for service in services:
            try:
                response = requests.head(service, timeout=5)
                connectivity[service] = response.status_code < 400
            except Exception:
                connectivity[service] = False
        
        return connectivity