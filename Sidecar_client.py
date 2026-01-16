"""
Sidecar Client Wrapper
Handles HTTP calls to AI sidecar with error handling and fallback
"""
import requests
import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class SidecarClient:
    """Client for AI sidecar API"""
    
    def __init__(self, base_url: str = "http://localhost:5000", timeout: int = 5):
        """
        Initialize sidecar client.
        
        Args:
            base_url: Sidecar API base URL
            timeout: Request timeout in seconds (default: 5)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def call_draft_api(self, request_data: Dict) -> Dict:
        """
        Call sidecar draft API.
        
        Args:
            request_data: Request payload
        
        Returns:
            dict: Sidecar response or fallback response
        """
        start_time = time.perf_counter()
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/draft",
                json=request_data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            
            # Handle HTTP errors
            if response.status_code == 400:
                logger.error(f"Sidecar 400 error: {response.text}")
                return self._error_fallback("bad_request", duration_ms)
            
            if response.status_code == 500:
                logger.error(f"Sidecar 500 error: {response.text}")
                # Retry once for 500 errors
                return self._retry_once(request_data, duration_ms)
            
            if response.status_code != 200:
                logger.error(f"Sidecar unexpected status {response.status_code}")
                return self._error_fallback("http_error", duration_ms)
            
            # Parse response
            try:
                data = response.json()
                logger.info(f"Sidecar call successful ({duration_ms}ms)")
                return data
            except ValueError as e:
                logger.error(f"Failed to parse sidecar response: {e}")
                # Retry once for parse errors
                return self._retry_once(request_data, duration_ms)
        
        except requests.exceptions.Timeout:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.warning(f"Sidecar timeout after {duration_ms}ms")
            return self._timeout_fallback(duration_ms)
        
        except requests.exceptions.ConnectionError as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Sidecar connection failed: {e}")
            return self._error_fallback("connection_refused", duration_ms)
        
        except Exception as e:
            duration_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"Sidecar unexpected error: {e}")
            return self._error_fallback("unknown", duration_ms)
    
    def _retry_once(self, request_data: Dict, initial_duration: int) -> Dict:
        """Retry request once after 1 second delay"""
        logger.info("Retrying sidecar call after 1 second...")
        time.sleep(1)
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/draft",
                json=request_data,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                logger.info("Sidecar retry successful")
                return data
            else:
                logger.error(f"Sidecar retry failed: {response.status_code}")
                return self._error_fallback("retry_failed", initial_duration)
        
        except Exception as e:
            logger.error(f"Sidecar retry exception: {e}")
            return self._error_fallback("retry_failed", initial_duration)
    
    def _timeout_fallback(self, duration_ms: int) -> Dict:
        """Return fallback response for timeout"""
        return {
            "success": False,
            "error": {
                "code": "timeout",
                "message": "Sidecar request timed out",
                "duration_ms": duration_ms
            }
        }
    
    def _error_fallback(self, error_code: str, duration_ms: int) -> Dict:
        """Return fallback response for errors"""
        return {
            "success": False,
            "error": {
                "code": error_code,
                "message": f"Sidecar error: {error_code}",
                "duration_ms": duration_ms
            }
        }
    
    def health_check(self) -> bool:
        """
        Check if sidecar is available.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=2
            )
            return response.status_code == 200
        except Exception:
            return False


# Global client instance
_client_instance: Optional[SidecarClient] = None


def get_sidecar_client() -> SidecarClient:
    """Get or create global sidecar client instance"""
    global _client_instance
    
    if _client_instance is None:
        _client_instance = SidecarClient()
    
    return _client_instance