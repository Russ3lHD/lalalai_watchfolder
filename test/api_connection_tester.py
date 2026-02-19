"""
API Connection Tester

Validates API connectivity without making actual processing requests.
Tests connection, authentication, rate limits, and basic health.
"""

import requests
import logging
import json
import time
from typing import Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ConnectionStatus(Enum):
    """Connection status indicators"""
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    RATE_LIMITED = "rate_limited"
    SERVICE_UNAVAILABLE = "service_unavailable"


@dataclass
class ConnectionTestResult:
    """Result of a connection test"""
    status: ConnectionStatus
    message: str
    response_time_ms: float
    http_code: Optional[int] = None
    error: Optional[str] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def is_successful(self) -> bool:
        """Check if connection test passed"""
        return self.status == ConnectionStatus.SUCCESS
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'status': self.status.value,
            'message': self.message,
            'response_time_ms': self.response_time_ms,
            'http_code': self.http_code,
            'error': self.error,
            'timestamp': self.timestamp.isoformat(),
            'successful': self.is_successful()
        }


class APIConnectionTester:
    """Tests Lalal AI API connectivity"""
    
    BASE_URL = "https://www.lalal.ai/api/v1/"
    
    def __init__(self, license_key: str):
        self.license_key = license_key
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.test_results = []
    
    def _setup_headers(self) -> Dict[str, str]:
        """Setup request headers"""
        return {
            'X-License-Key': self.license_key,
            'User-Agent': 'LalalAIVoiceCleanerTester/1.0.0'
        }
    
    def test_basic_connectivity(self, timeout: int = 10) -> ConnectionTestResult:
        """
        Test basic HTTP connectivity to API server
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            ConnectionTestResult with test outcome
        """
        self.logger.info("Testing basic connectivity...")
        
        start_time = time.time()
        
        try:
            response = self.session.head(
                f"{self.BASE_URL}voice_packs/list/",
                timeout=timeout,
                headers=self._setup_headers()
            )
            
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Accept 200 or 405 for a HEAD against a POST-only endpoint
            if response.status_code in [200, 405]:
                result = ConnectionTestResult(
                    status=ConnectionStatus.SUCCESS,
                    message="Basic connectivity successful",
                    response_time_ms=response_time,
                    http_code=response.status_code
                )
            else:
                result = ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"Unexpected status code: {response.status_code}",
                    response_time_ms=response_time,
                    http_code=response.status_code
                )
            
            self.test_results.append(result)
            return result
            
        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            result = ConnectionTestResult(
                status=ConnectionStatus.TIMEOUT,
                message=f"Request timeout after {timeout}s",
                response_time_ms=response_time,
                error="Timeout"
            )
            self.test_results.append(result)
            return result
            
        except requests.exceptions.ConnectionError as e:
            response_time = (time.time() - start_time) * 1000
            result = ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message="Connection failed",
                response_time_ms=response_time,
                error=str(e)
            )
            self.test_results.append(result)
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message="Unexpected error during connectivity test",
                response_time_ms=response_time,
                error=str(e)
            )
            self.test_results.append(result)
            return result
    
    def test_authentication(self, timeout: int = 10) -> ConnectionTestResult:
        """
        Test API authentication with license key
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            ConnectionTestResult with authentication status
        """
        self.logger.info("Testing authentication...")
        
        start_time = time.time()
        
        try:
            headers = self._setup_headers()
            response = self.session.post(
                f"{self.BASE_URL}voice_packs/list/",
                json={},
                timeout=timeout,
                headers=headers
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                result = ConnectionTestResult(
                    status=ConnectionStatus.SUCCESS,
                    message="Authentication successful",
                    response_time_ms=response_time,
                    http_code=response.status_code
                )
            elif response.status_code == 401:
                result = ConnectionTestResult(
                    status=ConnectionStatus.AUTH_ERROR,
                    message="Authentication failed - invalid license key",
                    response_time_ms=response_time,
                    http_code=response.status_code,
                    error="Unauthorized"
                )
            elif response.status_code == 403:
                result = ConnectionTestResult(
                    status=ConnectionStatus.AUTH_ERROR,
                    message="Authentication failed - license not authorized",
                    response_time_ms=response_time,
                    http_code=response.status_code,
                    error="Forbidden"
                )
            else:
                result = ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"Unexpected response: {response.status_code}",
                    response_time_ms=response_time,
                    http_code=response.status_code
                )
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message="Error during authentication test",
                response_time_ms=response_time,
                error=str(e)
            )
            self.test_results.append(result)
            return result
    
    def test_upload_endpoint(self, timeout: int = 10) -> ConnectionTestResult:
        """
        Test upload endpoint availability (without uploading)
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            ConnectionTestResult with upload endpoint status
        """
        self.logger.info("Testing upload endpoint...")
        
        start_time = time.time()
        
        try:
            headers = self._setup_headers()
            response = self.session.head(
                f"{self.BASE_URL}upload/",
                timeout=timeout,
                headers=headers
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 405]:  # 405 is expected for HEAD on POST-only endpoint
                result = ConnectionTestResult(
                    status=ConnectionStatus.SUCCESS,
                    message="Upload endpoint available",
                    response_time_ms=response_time,
                    http_code=response.status_code
                )
            elif response.status_code == 429:
                result = ConnectionTestResult(
                    status=ConnectionStatus.RATE_LIMITED,
                    message="Upload endpoint rate limited",
                    response_time_ms=response_time,
                    http_code=response.status_code,
                    error="Rate limit exceeded"
                )
            elif response.status_code == 503:
                result = ConnectionTestResult(
                    status=ConnectionStatus.SERVICE_UNAVAILABLE,
                    message="Upload endpoint unavailable",
                    response_time_ms=response_time,
                    http_code=response.status_code,
                    error="Service unavailable"
                )
            else:
                result = ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"Unexpected status: {response.status_code}",
                    response_time_ms=response_time,
                    http_code=response.status_code
                )
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message="Error testing upload endpoint",
                response_time_ms=response_time,
                error=str(e)
            )
            self.test_results.append(result)
            return result
    
    def test_processing_endpoint(self, timeout: int = 10) -> ConnectionTestResult:
        """
        Test processing endpoint availability
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            ConnectionTestResult with processing endpoint status
        """
        self.logger.info("Testing processing endpoint...")
        
        start_time = time.time()
        
        try:
            headers = self._setup_headers()
            response = self.session.head(
                f"{self.BASE_URL}split/stem_separator/",
                timeout=timeout,
                headers=headers
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code in [200, 405]:  # 405 is expected for HEAD on POST-only endpoint
                result = ConnectionTestResult(
                    status=ConnectionStatus.SUCCESS,
                    message="Processing endpoint available",
                    response_time_ms=response_time,
                    http_code=response.status_code
                )
            elif response.status_code == 429:
                result = ConnectionTestResult(
                    status=ConnectionStatus.RATE_LIMITED,
                    message="Processing endpoint rate limited",
                    response_time_ms=response_time,
                    http_code=response.status_code,
                    error="Rate limit exceeded"
                )
            elif response.status_code == 503:
                result = ConnectionTestResult(
                    status=ConnectionStatus.SERVICE_UNAVAILABLE,
                    message="Processing endpoint unavailable",
                    response_time_ms=response_time,
                    http_code=response.status_code,
                    error="Service unavailable"
                )
            else:
                result = ConnectionTestResult(
                    status=ConnectionStatus.FAILED,
                    message=f"Unexpected status: {response.status_code}",
                    response_time_ms=response_time,
                    http_code=response.status_code
                )
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            result = ConnectionTestResult(
                status=ConnectionStatus.FAILED,
                message="Error testing processing endpoint",
                response_time_ms=response_time,
                error=str(e)
            )
            self.test_results.append(result)
            return result
    
    def test_all(self, timeout: int = 10) -> Dict[str, ConnectionTestResult]:
        """
        Run all connection tests
        
        Args:
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with all test results
        """
        self.logger.info("Running comprehensive API connection tests...")
        
        results = {
            'connectivity': self.test_basic_connectivity(timeout),
            'authentication': self.test_authentication(timeout),
            'upload_endpoint': self.test_upload_endpoint(timeout),
            'processing_endpoint': self.test_processing_endpoint(timeout)
        }
        
        return results
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of all tests performed"""
        successful = sum(1 for r in self.test_results if r.is_successful())
        total = len(self.test_results)
        
        return {
            'total_tests': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'results': [r.to_dict() for r in self.test_results]
        }
    
    def print_test_report(self):
        """Print formatted test report"""
        print("\n" + "="*60)
        print("LALAL AI API CONNECTION TEST REPORT")
        print("="*60)
        
        for result in self.test_results:
            status_icon = "[PASS]" if result.is_successful() else "[FAIL]"
            print(f"\n{status_icon} {result.status.value.upper()}")
            print(f"   Message: {result.message}")
            print(f"   Response Time: {result.response_time_ms:.2f}ms")
            
            if result.http_code:
                print(f"   HTTP Code: {result.http_code}")
            
            if result.error:
                print(f"   Error: {result.error}")
        
        summary = self.get_test_summary()
        print(f"\n{'-'*60}")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Successful: {summary['successful']}")
        print(f"Failed: {summary['failed']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print("="*60 + "\n")
    
    def export_results(self, filepath: str) -> bool:
        """
        Export test results to JSON file
        
        Args:
            filepath: Path to export file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            summary = self.get_test_summary()
            
            with open(filepath, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            self.logger.info(f"Test results exported to {filepath}")
            return True
        except Exception as e:
            self.logger.error(f"Error exporting test results: {e}")
            return False


# Example usage and CLI interface
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) < 2:
        print("Usage: python api_connection_tester.py <license_key> [timeout]")
        print("Example: python api_connection_tester.py your_license_key 10")
        sys.exit(1)
    
    license_key = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    # Create tester and run all tests
    tester = APIConnectionTester(license_key)
    results = tester.test_all(timeout=timeout)
    
    # Print report
    tester.print_test_report()
    
    # Export results
    export_path = "api_connection_test_results.json"
    if tester.export_results(export_path):
        print(f"Results saved to {export_path}")
    
    # Exit with appropriate code
    summary = tester.get_test_summary()
    sys.exit(0 if summary['failed'] == 0 else 1)
