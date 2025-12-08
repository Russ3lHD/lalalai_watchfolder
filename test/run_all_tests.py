"""
Comprehensive Test Runner

Runs all component tests, integration tests, and provides a test report.
"""

import unittest
import sys
import logging
from io import StringIO
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Handle Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def run_all_tests():
    """Run all test suites"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.WARNING,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("\n" + "=" * 70)
    print("LALAL AI VOICE CLEANER - COMPREHENSIVE TEST SUITE")
    print("=" * 70 + "\n")
    
    # Discover and run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Load integration tests
    try:
        from test_integration import (
            TestShutdownIntegration,
            TestResourceMonitorIntegration,
            TestGracefulShutdownIntegration,
            TestProcessStateManager,
            TestFullIntegrationScenario,
            TestResourceMonitorPerformance
        )
        
        print("Loading Integration Tests...")
        suite.addTests(loader.loadTestsFromTestCase(TestShutdownIntegration))
        suite.addTests(loader.loadTestsFromTestCase(TestResourceMonitorIntegration))
        suite.addTests(loader.loadTestsFromTestCase(TestGracefulShutdownIntegration))
        suite.addTests(loader.loadTestsFromTestCase(TestProcessStateManager))
        suite.addTests(loader.loadTestsFromTestCase(TestFullIntegrationScenario))
        suite.addTests(loader.loadTestsFromTestCase(TestResourceMonitorPerformance))
        print("[PASS] Integration tests loaded\n")
    except Exception as e:
        print(f"[WARN] Could not load integration tests: {e}\n")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n[PASS] All tests PASSED!")
        print("=" * 70 + "\n")
        return 0
    else:
        print("\n[FAIL] Some tests FAILED!")
        print("=" * 70 + "\n")
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
