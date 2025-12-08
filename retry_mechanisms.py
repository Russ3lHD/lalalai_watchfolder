"""
Retry mechanisms and circuit breaker pattern for robust API operations
Provides fault tolerance and resilience for external service interactions
"""

import time
import logging
import threading
from typing import Callable, Any, Optional, Dict, List
from functools import wraps
from enum import Enum
from exceptions import (
    APITimeoutError, APIRateLimitError, APIServiceUnavailableError,
    APIAuthenticationError, APIError
)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascading failures
    """
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, 
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection
        """
        with self.lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.logger.info("Circuit breaker moved to HALF_OPEN state")
                else:
                    raise APIServiceUnavailableError(
                        f"Circuit breaker is OPEN. Service temporarily unavailable."
                    )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if self.last_failure_time is None:
            return True
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.logger.info("Circuit breaker recovered and moved to CLOSED state")
    
    def _on_failure(self):
        """Handle failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }


class RetryPolicy:
    """
    Configurable retry policy with exponential backoff
    """
    
    def __init__(self, max_attempts: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_multiplier: float = 2.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.logger = logging.getLogger(__name__)
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry policy
        """
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except (APITimeoutError, APIRateLimitError, APIServiceUnavailableError) as e:
                last_exception = e
                if attempt == self.max_attempts - 1:
                    self.logger.error(f"All {self.max_attempts} attempts failed. Last error: {str(e)}")
                    raise
                
                delay = self._calculate_delay(attempt)
                self.logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay:.2f}s...")
                time.sleep(delay)
            except APIAuthenticationError as e:
                # Don't retry authentication errors
                self.logger.error(f"Authentication failed, not retrying: {str(e)}")
                raise
            except Exception as e:
                # Don't retry other exceptions
                self.logger.error(f"Non-retryable error: {str(e)}")
                raise
        
        # Should not reach here, but just in case
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next attempt"""
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            # Add ±25% jitter
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0.1, delay)  # Minimum delay of 0.1 seconds


class APIClientWrapper:
    """
    Wrapper around API client with retry and circuit breaker protection
    """
    
    def __init__(self, api_client, retry_policy: RetryPolicy = None, 
                 circuit_breaker: CircuitBreaker = None):
        self.api_client = api_client
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.logger = logging.getLogger(__name__)
    
    def _protected_call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute API call with protection layers"""
        try:
            # Apply circuit breaker
            return self.circuit_breaker.call(self.retry_policy.execute, func, *args, **kwargs)
        except (APITimeoutError, APIRateLimitError, APIServiceUnavailableError) as e:
            # Log detailed error information
            self.logger.error(f"API call failed after retries and circuit breaker: {str(e)}")
            self.logger.error(f"Circuit breaker state: {self.circuit_breaker.get_state()}")
            raise
    
    def test_connection(self) -> bool:
        """Test API connection with protection"""
        try:
            self._protected_call(self.api_client.test_connection)
            return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def upload_file(self, file_path: str) -> Optional[str]:
        """Upload file with protection"""
        return self._protected_call(self.api_client.upload_file, file_path)
    
    def process_voice_cleanup(self, file_id: str, **options) -> Optional[str]:
        """Process voice cleanup with protection"""
        return self._protected_call(self.api_client.process_voice_cleanup, file_id, **options)
    
    def check_job_status(self, job_id: str):
        """Check job status with protection"""
        return self._protected_call(self.api_client.check_job_status, job_id)
    
    def download_processed_file(self, file_url: str, output_path: str) -> bool:
        """Download processed file with protection"""
        return self._protected_call(self.api_client.download_processed_file, file_url, output_path)
    
    def convert_voice(self, file_id: str, **options) -> Optional[str]:
        """Convert voice with protection"""
        return self._protected_call(self.api_client.convert_voice, file_id, **options)
    
    def get_circuit_breaker_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return self.circuit_breaker.get_state()


def retry_on_failure(max_attempts: int = 3, delay: float = 1.0, 
                    exceptions: tuple = (Exception,), backoff: float = 2.0):
    """
    Decorator for automatic retry on failure
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    
                    wait_time = delay * (backoff ** attempt)
                    logging.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            
            logging.error(f"All {max_attempts} attempts failed for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator


class HealthChecker:
    """
    Monitor and report on API client health
    """
    
    def __init__(self, api_client_wrapper: APIClientWrapper):
        self.api_client = api_client_wrapper
        self.logger = logging.getLogger(__name__)
    
    def check_health(self) -> Dict[str, Any]:
        """
        Perform comprehensive health check
        """
        health_status = {
            "overall_status": "healthy",
            "checks": {},
            "timestamp": time.time(),
            "details": {}
        }
        
        try:
            # Test connection
            connection_ok = self.api_client.test_connection()
            health_status["checks"]["connection"] = connection_ok
            
            if not connection_ok:
                health_status["overall_status"] = "unhealthy"
                health_status["details"]["connection_error"] = "Cannot connect to API"
            
            # Check circuit breaker state
            circuit_state = self.api_client.get_circuit_breaker_state()
            health_status["checks"]["circuit_breaker"] = circuit_state["state"] == CircuitState.CLOSED.value
            health_status["details"]["circuit_breaker"] = circuit_state
            
            if circuit_state["state"] == CircuitState.OPEN.value:
                health_status["overall_status"] = "degraded"
                health_status["details"]["circuit_breaker_open"] = "API circuit breaker is open"
            
            # Check if we have recent failures
            if circuit_state["failure_count"] > 0:
                health_status["details"]["recent_failures"] = circuit_state["failure_count"]
                if health_status["overall_status"] == "healthy":
                    health_status["overall_status"] = "degraded"
            
            return health_status
            
        except Exception as e:
            health_status["overall_status"] = "error"
            health_status["checks"]["health_check_failed"] = False
            health_status["details"]["error"] = str(e)
            self.logger.error(f"Health check failed: {str(e)}")
            return health_status
    
    def is_healthy(self) -> bool:
        """Quick health check - returns True if service is healthy"""
        health = self.check_health()
        return health["overall_status"] in ["healthy", "degraded"]  # Allow degraded state