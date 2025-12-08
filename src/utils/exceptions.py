"""
Custom exceptions for the Lalal AI Voice Cleaner application
Provides specific exception types for better error handling and debugging
"""


class LalalAICleanerError(Exception):
    """Base exception for all application errors"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class APIError(LalalAICleanerError):
    """Base exception for API-related errors"""
    pass


class APIAuthenticationError(APIError):
    """Raised when API authentication fails"""
    def __init__(self, message: str = "API authentication failed", details: dict = None):
        super().__init__(message, "API_AUTH_ERROR", details)


class APITimeoutError(APIError):
    """Raised when API request times out"""
    def __init__(self, message: str = "API request timed out", timeout_duration: float = None, details: dict = None):
        super().__init__(message, "API_TIMEOUT", details)
        self.timeout_duration = timeout_duration


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded"""
    def __init__(self, message: str = "API rate limit exceeded", retry_after: float = None, details: dict = None):
        super().__init__(message, "API_RATE_LIMIT", details)
        self.retry_after = retry_after


class APIServiceUnavailableError(APIError):
    """Raised when API service is unavailable"""
    def __init__(self, message: str = "API service unavailable", retry_after: float = None, details: dict = None):
        super().__init__(message, "API_SERVICE_UNAVAILABLE", details)
        self.retry_after = retry_after


class FileProcessingError(LalalAICleanerError):
    """Base exception for file processing errors"""
    pass


class FileNotFoundError(FileProcessingError):
    """Raised when a file is not found"""
    def __init__(self, file_path: str, message: str = None):
        if message is None:
            message = f"File not found: {file_path}"
        super().__init__(message, "FILE_NOT_FOUND", {"file_path": file_path})


class FileFormatError(FileProcessingError):
    """Raised when file format is not supported"""
    def __init__(self, file_path: str, supported_formats: list, message: str = None):
        if message is None:
            message = f"Unsupported file format: {file_path}"
        super().__init__(message, "FILE_FORMAT_ERROR", {
            "file_path": file_path,
            "supported_formats": supported_formats
        })


class FileCorruptedError(FileProcessingError):
    """Raised when file appears to be corrupted"""
    def __init__(self, file_path: str, message: str = None):
        if message is None:
            message = f"File appears to be corrupted: {file_path}"
        super().__init__(message, "FILE_CORRUPTED", {"file_path": file_path})


class FileSizeError(FileProcessingError):
    """Raised when file size exceeds limits"""
    def __init__(self, file_path: str, file_size: int, max_size: int, message: str = None):
        if message is None:
            message = f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
        super().__init__(message, "FILE_SIZE_ERROR", {
            "file_path": file_path,
            "file_size": file_size,
            "max_size": max_size
        })


class ConfigurationError(LalalAICleanerError):
    """Base exception for configuration-related errors"""
    pass


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration validation fails"""
    def __init__(self, message: str, invalid_fields: list = None, details: dict = None):
        super().__init__(message, "CONFIG_VALIDATION_ERROR", details)
        self.invalid_fields = invalid_fields or []


class ConfigurationEncryptionError(ConfigurationError):
    """Raised when configuration encryption/decryption fails"""
    def __init__(self, message: str = "Configuration encryption/decryption failed", details: dict = None):
        super().__init__(message, "CONFIG_ENCRYPTION_ERROR", details)


class ConfigurationFileError(ConfigurationError):
    """Raised when configuration file operations fail"""
    def __init__(self, message: str, config_file: str = None, details: dict = None):
        super().__init__(message, "CONFIG_FILE_ERROR", details)
        self.config_file = config_file


class ThreadingError(LalalAICleanerError):
    """Base exception for threading-related errors"""
    pass


class ThreadTimeoutError(ThreadingError):
    """Raised when a thread operation times out"""
    def __init__(self, message: str = "Thread operation timed out", timeout_duration: float = None, details: dict = None):
        super().__init__(message, "THREAD_TIMEOUT", details)
        self.timeout_duration = timeout_duration


class ThreadCleanupError(ThreadingError):
    """Raised when thread cleanup fails"""
    def __init__(self, message: str = "Thread cleanup failed", details: dict = None):
        super().__init__(message, "THREAD_CLEANUP_ERROR", details)


class ProcessingQueueError(LalalAICleanerError):
    """Base exception for processing queue errors"""
    pass


class QueueFullError(ProcessingQueueError):
    """Raised when processing queue is full"""
    def __init__(self, message: str = "Processing queue is full", queue_size: int = None, max_size: int = None, details: dict = None):
        super().__init__(message, "QUEUE_FULL", details)
        self.queue_size = queue_size
        self.max_size = max_size


class QueueCorruptionError(ProcessingQueueError):
    """Raised when processing queue is corrupted"""
    def __init__(self, message: str = "Processing queue is corrupted", details: dict = None):
        super().__init__(message, "QUEUE_CORRUPTION", details)


class HealthCheckError(LalalAICleanerError):
    """Base exception for health check failures"""
    pass


class SystemResourceError(HealthCheckError):
    """Raised when system resources are insufficient"""
    def __init__(self, message: str, resource_type: str = None, current_usage: float = None, threshold: float = None, details: dict = None):
        super().__init__(message, "SYSTEM_RESOURCE_ERROR", details)
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.threshold = threshold


class DependencyError(LalalAICleanerError):
    """Raised when a required dependency is missing or invalid"""
    def __init__(self, dependency_name: str, message: str = None, details: dict = None):
        if message is None:
            message = f"Required dependency missing or invalid: {dependency_name}"
        super().__init__(message, "DEPENDENCY_ERROR", details)
        self.dependency_name = dependency_name