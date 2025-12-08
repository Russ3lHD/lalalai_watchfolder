"""
Utility functions and helpers
"""

from .exceptions import (
    LalalAICleanerError, APIError, APIAuthenticationError, APITimeoutError,
    APIRateLimitError, APIServiceUnavailableError, FileProcessingError
)
from .file_validator import FileValidator, AtomicFileOperation
from .retry_mechanisms import CircuitBreaker, RetryPolicy, APIClientWrapper, HealthChecker
from .shutdown_manager import ShutdownManager, ThreadManager, FileHandleManager, ProcessStateManager
from .graceful_shutdown import (
    GracefulShutdownHandler, SafeShutdownCoordinator, OperationTracker, OperationStatus
)

__all__ = [
    "LalalAICleanerError", "APIError", "APIAuthenticationError", "APITimeoutError",
    "APIRateLimitError", "APIServiceUnavailableError", "FileProcessingError",
    "FileValidator", "AtomicFileOperation",
    "CircuitBreaker", "RetryPolicy", "APIClientWrapper", "HealthChecker",
    "ShutdownManager", "ThreadManager", "FileHandleManager", "ProcessStateManager",
    "GracefulShutdownHandler", "SafeShutdownCoordinator", "OperationTracker", "OperationStatus"
]
