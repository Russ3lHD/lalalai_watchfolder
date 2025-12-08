# Test Suite

This directory contains all unit tests and integration tests for the Lalal AI Voice Cleaner application.

## Files

- **test_integration.py** - Integration tests for stability components (shutdown, resources, graceful shutdown)
- **test_stability_improvements.py** - Comprehensive tests for all stability features
- **run_all_tests.py** - Test runner that executes all tests

## Running Tests

### Run all tests from the test directory:
```bash
cd test
python run_all_tests.py
```

### Run all tests from the project root:
```bash
python test/run_all_tests.py
```

### Run a specific test file:
```bash
cd test
python test_integration.py
```

```bash
cd test
python test_stability_improvements.py
```

## Test Coverage

The test suite covers:

1. **Shutdown Management**
   - Basic shutdown sequence
   - Thread manager shutdown
   - Multiple cleanup callbacks

2. **Resource Monitoring**
   - Temporary file creation and cleanup
   - Resource status reporting
   - Resource limit enforcement

3. **Graceful Shutdown**
   - Operation tracking
   - Shutdown readiness
   - Operation cancellation

4. **Process State**
   - State persistence
   - Default values

5. **Full Integration**
   - Complete application lifecycle
   - Resource monitoring performance

6. **Stability Improvements**
   - Custom exceptions
   - Retry policies
   - Circuit breaker
   - File validation
   - Atomic file operations
   - Health monitoring
   - Configuration management
   - Error recovery scenarios
   - Performance under load
   - Configuration migration

## Import Notes

All test files use parent directory imports via `sys.path.insert(0, ...)` to allow:
- Running tests from the `/test` directory: `python run_all_tests.py`
- Running tests from the project root: `python test/run_all_tests.py`
- Running individual test files: `python test/test_integration.py`

## Test Results

After running tests, you'll see a summary showing:
- Total tests run
- Passed tests
- Failed tests
- Any errors encountered

All tests should pass when the application is properly configured.
