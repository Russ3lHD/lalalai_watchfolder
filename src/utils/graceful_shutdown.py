"""
Graceful Shutdown Handler

Coordinates safe application shutdown with user warnings,
active operation tracking, and resource cleanup.
"""

import logging
import threading
import time
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class OperationStatus(Enum):
    """Status of an operation"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ActiveOperation:
    """Represents an active operation"""
    operation_id: str
    operation_type: str
    description: str
    start_time: datetime = field(default_factory=datetime.now)
    status: OperationStatus = OperationStatus.RUNNING
    cancellable: bool = True
    cancel_callback: Optional[Callable[[], None]] = None
    
    def get_duration_seconds(self) -> float:
        """Get operation duration in seconds"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_status_string(self) -> str:
        """Get human-readable status"""
        duration = self.get_duration_seconds()
        return f"{self.description} ({duration:.1f}s, {self.status.value})"


class OperationTracker:
    """Tracks active operations for shutdown coordination"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.operations: Dict[str, ActiveOperation] = {}
        self.operations_lock = threading.Lock()
    
    def start_operation(self, operation_id: str, operation_type: str, 
                       description: str, cancellable: bool = True,
                       cancel_callback: Optional[Callable[[], None]] = None) -> ActiveOperation:
        """Register an operation as active"""
        operation = ActiveOperation(
            operation_id=operation_id,
            operation_type=operation_type,
            description=description,
            cancellable=cancellable,
            cancel_callback=cancel_callback
        )
        
        with self.operations_lock:
            self.operations[operation_id] = operation
        
        self.logger.debug(f"Operation started: {operation.get_status_string()}")
        return operation
    
    def update_operation_status(self, operation_id: str, status: OperationStatus):
        """Update operation status"""
        with self.operations_lock:
            if operation_id in self.operations:
                self.operations[operation_id].status = status
                self.logger.debug(f"Operation status updated: {operation_id} -> {status.value}")
    
    def complete_operation(self, operation_id: str):
        """Mark operation as completed"""
        self.update_operation_status(operation_id, OperationStatus.COMPLETED)
        
        with self.operations_lock:
            if operation_id in self.operations:
                operation = self.operations.pop(operation_id)
                self.logger.debug(f"Operation completed: {operation.get_status_string()}")
    
    def get_active_operations(self) -> List[ActiveOperation]:
        """Get list of all active operations"""
        with self.operations_lock:
            return list(self.operations.values())
    
    def get_operation_count(self) -> int:
        """Get count of active operations"""
        with self.operations_lock:
            return len(self.operations)
    
    def get_cancellable_operations(self) -> List[ActiveOperation]:
        """Get operations that can be cancelled"""
        return [op for op in self.get_active_operations() if op.cancellable]
    
    def cancel_all_operations(self, timeout: float = 10.0) -> bool:
        """Attempt to cancel all cancellable operations"""
        cancellable_ops = self.get_cancellable_operations()
        
        if not cancellable_ops:
            self.logger.info("No cancellable operations")
            return True
        
        self.logger.info(f"Cancelling {len(cancellable_ops)} operations...")
        
        start_time = time.time()
        
        for operation in cancellable_ops:
            elapsed = time.time() - start_time
            remaining = timeout - elapsed
            
            if remaining <= 0:
                self.logger.warning(f"Operation cancellation timeout reached")
                return False
            
            try:
                if operation.cancel_callback:
                    self.logger.debug(f"Cancelling: {operation.description}")
                    operation.cancel_callback()
                    operation.status = OperationStatus.CANCELLED
            except Exception as e:
                self.logger.error(f"Error cancelling operation {operation.operation_id}: {e}")
        
        # Wait for operations to complete cancellation
        wait_time = time.time()
        while self.get_operation_count() > 0 and (time.time() - wait_time) < remaining:
            time.sleep(0.1)
        
        return self.get_operation_count() == 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of active operations"""
        operations = self.get_active_operations()
        
        return {
            'total_count': len(operations),
            'by_type': self._group_by_type(operations),
            'operations': [
                {
                    'id': op.operation_id,
                    'type': op.operation_type,
                    'description': op.description,
                    'duration_seconds': op.get_duration_seconds(),
                    'status': op.status.value,
                    'cancellable': op.cancellable
                }
                for op in operations
            ]
        }
    
    def _group_by_type(self, operations: List[ActiveOperation]) -> Dict[str, int]:
        """Group operations by type"""
        groups = {}
        for op in operations:
            groups[op.operation_type] = groups.get(op.operation_type, 0) + 1
        return groups


class GracefulShutdownHandler:
    """Handles graceful shutdown with operation coordination"""
    
    def __init__(self, shutdown_manager=None):
        self.logger = logging.getLogger(__name__)
        self.operation_tracker = OperationTracker()
        self.shutdown_manager = shutdown_manager
        self.shutdown_callbacks: List[Callable[[], None]] = []
        self.max_shutdown_wait = 60  # Maximum seconds to wait for shutdown
        
        if shutdown_manager:
            shutdown_manager.register_cleanup_callback(self._execute_shutdown)
    
    def register_operation(self, operation_id: str, operation_type: str,
                          description: str, cancellable: bool = True,
                          cancel_callback: Optional[Callable[[], None]] = None) -> ActiveOperation:
        """Register an active operation"""
        return self.operation_tracker.start_operation(
            operation_id, operation_type, description, cancellable, cancel_callback
        )
    
    def complete_operation(self, operation_id: str):
        """Mark operation as completed"""
        self.operation_tracker.complete_operation(operation_id)
    
    def register_shutdown_callback(self, callback: Callable[[], None]):
        """Register a callback to run during shutdown"""
        self.shutdown_callbacks.append(callback)
    
    def _execute_shutdown(self):
        """Execute shutdown sequence"""
        self.logger.info("Initiating graceful shutdown...")
        
        # Try to cancel all active operations
        operations_summary = self.operation_tracker.get_summary()
        self.logger.info(f"Active operations: {operations_summary['total_count']}")
        
        if operations_summary['total_count'] > 0:
            self.logger.info("Attempting to cancel active operations...")
            self.operation_tracker.cancel_all_operations(timeout=30.0)
        
        # Execute shutdown callbacks
        for callback in self.shutdown_callbacks:
            try:
                callback()
            except Exception as e:
                self.logger.error(f"Error in shutdown callback: {e}")
        
        self.logger.info("Graceful shutdown completed")
    
    def should_allow_shutdown(self) -> bool:
        """Determine if shutdown should be allowed"""
        # Allow shutdown if no operations or all are completed
        return self.operation_tracker.get_operation_count() == 0
    
    def get_shutdown_status(self) -> Dict[str, Any]:
        """Get shutdown readiness status"""
        operations_summary = self.operation_tracker.get_summary()
        
        return {
            'ready_for_shutdown': self.should_allow_shutdown(),
            'active_operations': operations_summary['total_count'],
            'operations_by_type': operations_summary['by_type'],
            'operations': operations_summary['operations']
        }


class SafeShutdownCoordinator:
    """Coordinates safe shutdown across multiple components"""
    
    def __init__(self, shutdown_manager=None, resource_manager=None):
        self.logger = logging.getLogger(__name__)
        self.shutdown_manager = shutdown_manager
        self.resource_manager = resource_manager
        self.graceful_handler = GracefulShutdownHandler(shutdown_manager)
        self.pre_shutdown_callbacks: List[Callable[[], None]] = []
    
    def register_pre_shutdown_callback(self, callback: Callable[[], None]):
        """Register callback to run before shutdown begins"""
        self.pre_shutdown_callbacks.append(callback)
    
    def prepare_for_shutdown(self) -> bool:
        """Prepare application for shutdown"""
        self.logger.info("Preparing for shutdown...")
        
        try:
            # Execute pre-shutdown callbacks
            for callback in self.pre_shutdown_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.error(f"Error in pre-shutdown callback: {e}")
            
            # Enforce resource limits if available
            if self.resource_manager:
                self.resource_manager.enforce_resource_limits()
            
            return True
        except Exception as e:
            self.logger.error(f"Error preparing for shutdown: {e}")
            return False
    
    def execute_shutdown(self):
        """Execute full shutdown sequence"""
        if not self.prepare_for_shutdown():
            self.logger.warning("Shutdown preparation had errors, continuing anyway")
        
        if self.shutdown_manager:
            self.shutdown_manager.initiate_shutdown()
    
    def get_shutdown_readiness(self) -> Dict[str, Any]:
        """Get detailed shutdown readiness status"""
        return {
            'graceful_shutdown_status': self.graceful_handler.get_shutdown_status(),
            'ready': self.graceful_handler.should_allow_shutdown(),
            'timestamp': datetime.now().isoformat()
        }
