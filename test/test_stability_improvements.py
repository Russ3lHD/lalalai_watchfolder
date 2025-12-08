#!/usr/bin/env python3
"""
Comprehensive test suite for stability improvements
Tests all new stability components and integration
"""

import sys
import time
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all stability components
from src.utils.exceptions import (
    LalalAICleanerError, APIError, FileProcessingError, 
    ConfigurationError, APIAuthenticationError, APITimeoutError,
    APIServiceUnavailableError, FileNotFoundError, FileFormatError, FileSizeError
)
from src.utils.retry_mechanisms import RetryPolicy, CircuitBreaker, APIClientWrapper, HealthChecker
from src.utils.file_validator import FileValidator, AtomicFileOperation
from src.monitoring.health_monitor import HealthMonitor, SystemHealth, HealthMetric
from src.config.enhanced_config_manager import EnhancedConfigManager, ConfigSchema


class StabilityTestSuite:
    """
    Comprehensive test suite for stability improvements
    """
    
    def __init__(self):
        self.test_dir = None
        self.logger = logging.getLogger(__name__)
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
    
    def setup_test_environment(self):
        """Set up test environment"""
        self.test_dir = Path(tempfile.mkdtemp(prefix='stability_test_'))
        self.logger.info(f"Test environment created: {self.test_dir}")
    
    def cleanup_test_environment(self):
        """Clean up test environment"""
        if self.test_dir and self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            self.logger.info("Test environment cleaned up")
    
    def run_test(self, test_name: str, test_func):
        """Run individual test with error handling"""
        self.logger.info(f"Running test: {test_name}")
        try:
            result = test_func()
            if result:
                self.passed_tests += 1
                self.test_results.append((test_name, "PASS", None))
                self.logger.info(f"✓ {test_name} passed")
            else:
                self.failed_tests += 1
                self.test_results.append((test_name, "FAIL", "Test returned False"))
                self.logger.error(f"✗ {test_name} failed")
        except Exception as e:
            self.failed_tests += 1
            self.test_results.append((test_name, "ERROR", str(e)))
            self.logger.error(f"✗ {test_name} failed with exception: {str(e)}")
    
    def test_custom_exceptions(self):
        """Test custom exception classes"""
        # Test base exception
        try:
            raise LalalAICleanerError("Test error", "TEST_CODE", {"key": "value"})
        except LalalAICleanerError as e:
            assert e.message == "Test error"
            assert e.error_code == "TEST_CODE"
            assert e.details == {"key": "value"}
        
        # Test API exceptions
        try:
            raise APIAuthenticationError()
        except APIAuthenticationError as e:
            assert "authentication failed" in str(e).lower()
        
        try:
            raise APITimeoutError("Timeout", 30.0)
        except APITimeoutError as e:
            assert e.timeout_duration == 30.0
        
        # Test file exceptions
        try:
            raise FileNotFoundError("/test/path")
        except FileNotFoundError as e:
            assert "/test/path" in str(e)
        
        try:
            raise FileSizeError("/test/file", 1000, 500)
        except FileSizeError as e:
            assert "1000" in str(e)
            assert "500" in str(e)
        
        return True
    
    def test_retry_policy(self):
        """Test retry policy functionality"""
        retry_policy = RetryPolicy(max_attempts=3, base_delay=0.1)
        
        # Test successful call
        def success_func():
            return "success"
        
        result = retry_policy.execute(success_func)
        assert result == "success"
        
        # Test retry with temporary failure
        call_count = 0
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APITimeoutError("Temporary failure")
            return "success"
        
        result = retry_policy.execute(failing_func)
        assert result == "success"
        assert call_count == 3
        
        return True
    
    def test_circuit_breaker(self):
        """Test circuit breaker functionality"""
        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)
        
        # Test normal operation
        def success_func():
            return "success"
        
        result = circuit_breaker.call(success_func)
        assert result == "success"
        assert circuit_breaker.state.value == "closed"
        
        # Test failure threshold
        def always_fail():
            raise Exception("Always fails")
        
        try:
            circuit_breaker.call(always_fail)
        except:
            pass
        
        try:
            circuit_breaker.call(always_fail)
        except:
            pass
        
        # Should open circuit after failures
        assert circuit_breaker.state.value == "open"
        
        # Should reject calls when open
        try:
            circuit_breaker.call(success_func)
            assert False, "Should have raised exception"
        except APIServiceUnavailableError:
            pass  # Expected
        
        return True
    
    def test_file_validator(self):
        """Test file validation functionality"""
        validator = FileValidator()
        
        # Create test file
        assert self.test_dir is not None, "Test directory not initialized"
        test_file = self.test_dir / "test.txt"
        test_file.write_text("test content")
        
        # Test format checking
        assert not validator.is_supported_format("test.txt")
        assert validator.is_supported_format("test.mp3")
        
        # Test supported formats
        formats = validator.get_supported_formats()
        assert "mp3" in formats
        assert "wav" in formats
        
        # Test file info
        file_info = validator._get_file_info(str(test_file))
        assert file_info["name"] == "test.txt"
        assert file_info["size"] == 12
        
        return True
    
    def test_atomic_file_operations(self):
        """Test atomic file operations"""
        atomic_ops = AtomicFileOperation()
        
        # Test atomic write
        assert self.test_dir is not None, "Test directory not initialized"
        test_file = self.test_dir / "atomic_test.txt"
        data = b"test data for atomic operation"
        
        success = atomic_ops.atomic_write(str(test_file), data)
        assert success
        assert test_file.exists()
        assert test_file.read_bytes() == data
        
        # Test atomic move
        source_file = self.test_dir / "source.txt"
        dest_file = self.test_dir / "destination.txt"
        
        source_file.write_bytes(b"move test")
        success = atomic_ops.atomic_move(str(source_file), str(dest_file))
        assert success
        assert not source_file.exists()
        assert dest_file.exists()
        assert dest_file.read_bytes() == b"move test"
        
        return True
    
    def test_health_monitor(self):
        """Test health monitoring functionality"""
        config = {'monitoring_interval': 1}
        health_monitor = HealthMonitor(config)
        
        # Test health check
        health_status = health_monitor.check_system_health()
        assert isinstance(health_status, SystemHealth)
        assert health_status.timestamp > 0
        assert health_status.uptime >= 0
        assert len(health_status.metrics) > 0
        
        # Test health summary
        summary = health_monitor.get_health_summary()
        assert "current_status" in summary
        assert "uptime_hours" in summary
        assert "memory_usage" in summary
        
        # Test health callback
        callback_called = []
        def health_callback(health_status):
            callback_called.append(health_status.overall_status)
        
        health_monitor.add_health_callback(health_callback)
        health_monitor._process_health_status(health_status)
        
        assert len(callback_called) > 0
        
        return True
    
    def test_enhanced_config_manager(self):
        """Test enhanced configuration manager"""
        assert self.test_dir is not None, "Test directory not initialized"
        config_dir = self.test_dir / "config_test"
        config_manager = EnhancedConfigManager(config_dir)
        
        # Test schema validation
        schema = ConfigSchema()
        test_config = {
            'auto_start': True,
            'noise_cancelling': 1,
            'processing_mode': 'voice_cleanup'
        }
        
        validation_result = schema.validate_config(test_config)
        assert validation_result['is_valid']
        
        # Test config save and load
        test_config = {
            'auto_start': False,
            'noise_cancelling': 2,
            'stem': 'voice',
            'splitter': 'perseus'
        }
        
        success = config_manager.save_config(test_config)
        assert success
        
        loaded_config = config_manager.load_config()
        assert loaded_config is not None
        assert loaded_config['auto_start'] == False
        assert loaded_config['noise_cancelling'] == 2
        
        # Test backup functionality
        backups = config_manager.list_backups()
        assert len(backups) >= 1
        
        return True
    
    def test_integration_health_monitor_config(self):
        """Test integration between health monitor and config manager"""
        assert self.test_dir is not None, "Test directory not initialized"
        config_dir = self.test_dir / "integration_test"
        config_manager = EnhancedConfigManager(config_dir)
        
        # Save config with health monitoring settings
        health_config = {
            'health_check_interval': 10,
            'max_queue_size': 50
        }
        
        success = config_manager.save_config(health_config)
        assert success
        
        # Load config and use in health monitor
        loaded_config = config_manager.load_config()
        assert loaded_config is not None, "Failed to load configuration"
        health_monitor = HealthMonitor({
            'monitoring_interval': loaded_config.get('health_check_interval', 30)
        })
        
        health_status = health_monitor.check_system_health()
        assert health_status is not None
        
        return True
    
    def test_error_recovery_scenarios(self):
        """Test various error recovery scenarios"""
        
        # Test API client wrapper with mock API
        mock_api_client = Mock()
        mock_api_client.test_connection.return_value = True
        mock_api_client.upload_file.return_value = "file_id_123"
        
        api_wrapper = APIClientWrapper(mock_api_client)
        
        # Test successful operations
        assert api_wrapper.test_connection()
        file_id = api_wrapper.upload_file("/test/file.mp3")
        assert file_id == "file_id_123"
        
        # Test circuit breaker state
        state = api_wrapper.get_circuit_breaker_state()
        assert 'state' in state
        assert 'failure_count' in state
        
        return True
    
    def test_performance_under_load(self):
        """Test performance under various load conditions"""
        
        # Test file validator performance
        validator = FileValidator()
        
        # Create multiple test files
        assert self.test_dir is not None, "Test directory not initialized"
        test_files = []
        for i in range(10):
            test_file = self.test_dir / f"test_{i}.txt"
            test_file.write_text(f"test content {i}")
            test_files.append(test_file)
        
        start_time = time.time()
        
        # Validate multiple files
        for test_file in test_files:
            validation = validator.validate_file(str(test_file))
            assert validation['is_valid']
        
        end_time = time.time()
        
        # Should process 10 files in reasonable time
        assert (end_time - start_time) < 5.0
        
        return True
    
    def test_configuration_migration(self):
        """Test configuration migration scenarios"""
        assert self.test_dir is not None, "Test directory not initialized"
        config_dir = self.test_dir / "migration_test"
        config_manager = EnhancedConfigManager(config_dir)
        
        # Create old format config
        old_config = {
            'license_key': 'old_license_key',
            'auto_start': True,
            'noise_cancelling': 1
        }
        
        # Save old config
        success = config_manager.save_config(old_config)
        assert success
        
        # Load and verify it works with new format
        loaded_config = config_manager.load_config()
        assert loaded_config is not None
        assert 'auto_start' in loaded_config
        
        # Verify schema validation works
        schema = ConfigSchema()
        validation = schema.validate_config(loaded_config)
        assert validation['is_valid'] or len(validation['warnings']) > 0
        
        return True
    
    def run_all_tests(self):
        """Run all stability tests"""
        self.logger.info("Starting stability test suite")
        self.logger.info("=" * 60)
        
        # Setup
        self.setup_test_environment()
        
        try:
            # Run all tests
            tests = [
                ("Custom Exceptions", self.test_custom_exceptions),
                ("Retry Policy", self.test_retry_policy),
                ("Circuit Breaker", self.test_circuit_breaker),
                ("File Validator", self.test_file_validator),
                ("Atomic File Operations", self.test_atomic_file_operations),
                ("Health Monitor", self.test_health_monitor),
                ("Enhanced Config Manager", self.test_enhanced_config_manager),
                ("Health Monitor + Config Integration", self.test_integration_health_monitor_config),
                ("Error Recovery Scenarios", self.test_error_recovery_scenarios),
                ("Performance Under Load", self.test_performance_under_load),
                ("Configuration Migration", self.test_configuration_migration)
            ]
            
            for test_name, test_func in tests:
                self.run_test(test_name, test_func)
        
        finally:
            # Cleanup
            self.cleanup_test_environment()
        
        # Print results
        self.print_test_results()
    
    def print_test_results(self):
        """Print test results summary"""
        self.logger.info("=" * 60)
        self.logger.info("STABILITY TEST RESULTS")
        self.logger.info("=" * 60)
        
        total_tests = self.passed_tests + self.failed_tests
        
        for test_name, status, error in self.test_results:
            if status == "PASS":
                self.logger.info(f"✓ {test_name}")
            elif status == "FAIL":
                self.logger.error(f"✗ {test_name}: {error}")
            else:  # ERROR
                self.logger.error(f"✗ {test_name}: ERROR - {error}")
        
        self.logger.info("=" * 60)
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Passed: {self.passed_tests}")
        self.logger.info(f"Failed: {self.failed_tests}")
        
        if self.failed_tests == 0:
            self.logger.info("🎉 All stability tests PASSED!")
        else:
            failure_rate = (self.failed_tests / total_tests) * 100
            self.logger.warning(f"⚠️  {failure_rate:.1f}% test failure rate")
        
        self.logger.info("=" * 60)


def main():
    """Main test runner"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run test suite
    test_suite = StabilityTestSuite()
    test_suite.run_all_tests()
    
    # Return appropriate exit code
    return 0 if test_suite.failed_tests == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
