"""
Integration Tests for Stability Components

Tests all stability components working together in an integrated environment.
"""

import unittest
import logging
import tempfile
import threading
import time
import json
import sys
from pathlib import Path
from typing import List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from shutdown_manager import ShutdownManager, ThreadManager, ProcessStateManager
from resource_monitor import ResourceManager, TempFileManager, ProcessResourceMonitor
from graceful_shutdown import SafeShutdownCoordinator, OperationStatus, OperationTracker


class TestShutdownIntegration(unittest.TestCase):
    """Test shutdown manager integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        logging.basicConfig(level=logging.INFO)
        self.shutdown_manager = ShutdownManager()
        self.thread_manager = ThreadManager(self.shutdown_manager)
    
    def test_basic_shutdown_sequence(self):
        """Test basic shutdown sequence"""
        cleanup_called = []
        
        def cleanup():
            cleanup_called.append(True)
        
        self.shutdown_manager.register_cleanup_callback(cleanup)
        self.shutdown_manager.initiate_shutdown()
        
        self.assertTrue(len(cleanup_called) > 0)
        self.assertTrue(self.shutdown_manager.is_shutdown_requested())
    
    def test_thread_manager_shutdown(self):
        """Test thread manager shutdown"""
        # Create a test thread
        def worker():
            for i in range(10):
                if not self.shutdown_manager.is_shutdown_requested():
                    time.sleep(0.1)
        
        thread = threading.Thread(target=worker, name="TestWorker")
        self.thread_manager.register_thread(thread)
        thread.start()
        
        # Verify thread is active
        self.assertTrue(thread.is_alive())
        
        # Trigger shutdown
        self.shutdown_manager.initiate_shutdown()
        
        # Wait a bit for thread to finish
        time.sleep(0.5)
    
    def test_multiple_cleanup_callbacks(self):
        """Test multiple cleanup callbacks are executed"""
        executed = []
        
        def callback1():
            executed.append(1)
        
        def callback2():
            executed.append(2)
        
        def callback3():
            executed.append(3)
        
        self.shutdown_manager.register_cleanup_callback(callback1)
        self.shutdown_manager.register_cleanup_callback(callback2)
        self.shutdown_manager.register_cleanup_callback(callback3)
        
        self.shutdown_manager.initiate_shutdown()
        
        self.assertEqual(len(executed), 3)
        self.assertIn(1, executed)
        self.assertIn(2, executed)
        self.assertIn(3, executed)


class TestResourceMonitorIntegration(unittest.TestCase):
    """Test resource monitor integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.shutdown_manager = ShutdownManager()
        self.resource_manager = ResourceManager(self.shutdown_manager)
    
    def test_temp_file_creation_and_cleanup(self):
        """Test temp file creation and cleanup"""
        # Create temp files
        temp_file = self.resource_manager.temp_manager.create_temp_file()
        
        self.assertTrue(temp_file.exists())
        
        # Write some data
        temp_file.write_text("test data")
        self.assertTrue(temp_file.stat().st_size > 0)
        
        # Cleanup
        self.resource_manager.cleanup_all_resources()
    
    def test_resource_status_reporting(self):
        """Test resource status reporting"""
        status = self.resource_manager.get_resource_status()
        
        self.assertIsNotNone(status)
        self.assertIn('healthy', status)
        self.assertIn('warnings', status)
        self.assertIn('resource_info', status)
    
    def test_resource_limit_enforcement(self):
        """Test resource limit enforcement"""
        # Get initial status
        initial_status = self.resource_manager.get_resource_status()
        
        # Enforce limits
        self.resource_manager.enforce_resource_limits()
        
        # Get status after enforcement
        final_status = self.resource_manager.get_resource_status()
        
        # Should still be running
        self.assertIsNotNone(final_status)


class TestGracefulShutdownIntegration(unittest.TestCase):
    """Test graceful shutdown integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.shutdown_manager = ShutdownManager()
        self.resource_manager = ResourceManager(self.shutdown_manager)
        self.coordinator = SafeShutdownCoordinator(self.shutdown_manager, self.resource_manager)
    
    def test_operation_tracking(self):
        """Test operation tracking"""
        # Register an operation
        operation = self.coordinator.graceful_handler.register_operation(
            operation_id='test_op_1',
            operation_type='test',
            description='Test operation',
            cancellable=True
        )
        
        self.assertIsNotNone(operation)
        self.assertEqual(operation.operation_id, 'test_op_1')
        
        # Verify it's tracked
        ops = self.coordinator.graceful_handler.operation_tracker.get_active_operations()
        self.assertEqual(len(ops), 1)
        
        # Complete operation
        self.coordinator.graceful_handler.complete_operation('test_op_1')
        
        # Verify it's removed
        ops = self.coordinator.graceful_handler.operation_tracker.get_active_operations()
        self.assertEqual(len(ops), 0)
    
    def test_shutdown_readiness(self):
        """Test shutdown readiness checking"""
        # Should be ready when no operations
        self.assertTrue(self.coordinator.graceful_handler.should_allow_shutdown())
        
        # Register operation
        self.coordinator.graceful_handler.register_operation(
            operation_id='op_1',
            operation_type='test',
            description='Test',
            cancellable=True
        )
        
        # Should not be ready
        self.assertFalse(self.coordinator.graceful_handler.should_allow_shutdown())
        
        # Complete operation
        self.coordinator.graceful_handler.complete_operation('op_1')
        
        # Should be ready again
        self.assertTrue(self.coordinator.graceful_handler.should_allow_shutdown())
    
    def test_operation_cancellation(self):
        """Test operation cancellation"""
        cancelled_ops = []
        
        def cancel_callback():
            cancelled_ops.append(True)
        
        # Register cancellable operation
        self.coordinator.graceful_handler.register_operation(
            operation_id='cancel_op_1',
            operation_type='test',
            description='Cancellable operation',
            cancellable=True,
            cancel_callback=cancel_callback
        )
        
        # Cancel all operations
        success = self.coordinator.graceful_handler.operation_tracker.cancel_all_operations()
        
        # Callback should be called
        self.assertTrue(len(cancelled_ops) > 0)


class TestProcessStateManager(unittest.TestCase):
    """Test process state manager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "test_state.json"
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_state_persistence(self):
        """Test state persistence"""
        manager = ProcessStateManager(str(self.state_file))
        
        # Save state
        manager.save_state('test_key', 'test_value')
        manager.save_state('counter', 42)
        
        # Verify file was created
        self.assertTrue(self.state_file.exists())
        
        # Create new manager and load state
        manager2 = ProcessStateManager(str(self.state_file))
        
        self.assertEqual(manager2.get_state('test_key'), 'test_value')
        self.assertEqual(manager2.get_state('counter'), 42)
    
    def test_state_default_values(self):
        """Test state with default values"""
        manager = ProcessStateManager(str(self.state_file))
        
        # Get non-existent key with default
        value = manager.get_state('nonexistent', 'default_value')
        self.assertEqual(value, 'default_value')


class TestFullIntegrationScenario(unittest.TestCase):
    """Test full integration scenario with all components"""
    
    def setUp(self):
        """Set up test fixtures"""
        logging.basicConfig(level=logging.INFO)
    
    def test_complete_application_lifecycle(self):
        """Test complete application lifecycle"""
        # Initialize all components
        shutdown_manager = ShutdownManager()
        thread_manager = ThreadManager(shutdown_manager)
        resource_manager = ResourceManager(shutdown_manager)
        shutdown_coordinator = SafeShutdownCoordinator(shutdown_manager, resource_manager)
        
        cleanup_log = []
        
        def on_cleanup():
            cleanup_log.append('cleanup')
        
        shutdown_manager.register_cleanup_callback(on_cleanup)
        
        # Simulate application operations
        op1 = shutdown_coordinator.graceful_handler.register_operation(
            operation_id='op_1',
            operation_type='processing',
            description='Processing file 1',
            cancellable=True
        )
        
        op2 = shutdown_coordinator.graceful_handler.register_operation(
            operation_id='op_2',
            operation_type='upload',
            description='Uploading results',
            cancellable=True
        )
        
        # Verify operations are tracked
        self.assertEqual(
            shutdown_coordinator.graceful_handler.operation_tracker.get_operation_count(),
            2
        )
        
        # Complete operations
        shutdown_coordinator.graceful_handler.complete_operation('op_1')
        self.assertEqual(
            shutdown_coordinator.graceful_handler.operation_tracker.get_operation_count(),
            1
        )
        
        shutdown_coordinator.graceful_handler.complete_operation('op_2')
        self.assertEqual(
            shutdown_coordinator.graceful_handler.operation_tracker.get_operation_count(),
            0
        )
        
        # Verify shutdown is ready
        self.assertTrue(shutdown_coordinator.graceful_handler.should_allow_shutdown())
        
        # Execute shutdown
        shutdown_coordinator.execute_shutdown()
        
        # Verify cleanup was called
        self.assertTrue(len(cleanup_log) > 0)


class TestResourceMonitorPerformance(unittest.TestCase):
    """Test resource monitor performance characteristics"""
    
    def test_temp_file_manager_performance(self):
        """Test temp file manager performance"""
        manager = TempFileManager()
        
        start_time = time.time()
        
        # Create multiple temp files
        for i in range(10):
            temp_file = manager.create_temp_file()
            temp_file.write_text(f"test content {i}")
        
        elapsed = time.time() - start_time
        
        # Should be reasonably fast (less than 1 second)
        self.assertLess(elapsed, 1.0)
        
        # Cleanup
        manager.cleanup_all_temps()
    
    def test_process_monitor_performance(self):
        """Test process monitor performance"""
        monitor = ProcessResourceMonitor()
        
        start_time = time.time()
        
        # Get resource info multiple times
        for i in range(10):
            info = monitor.get_resource_info()
            self.assertIsNotNone(info)
        
        elapsed = time.time() - start_time
        
        # Should be fast (less than 2 seconds for 10 iterations)
        self.assertLess(elapsed, 2.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
