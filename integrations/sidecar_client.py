# integrations/sidecar_client.py

"""
Sidecar HTTP client for FutureHub
Handles communication with external AI sidecar service
Day 1: Basic request/timeout/fallback only - NO RETRIES
"""

import requests
from typing import Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SidecarResponse:
    """Response from sidecar service"""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    status_code: Optional[int]
    duration_ms: Optional[float]
    timed_out: bool = False


class SidecarClient:
    """
    HTTP client for sidecar service
    Day 1 scope: timeout + graceful fallback only
    NO retries, NO complex error handling
    """
    
    DEFAULT_TIMEOUT = 10.0  # seconds
    
    def __init__(self, base_url: str, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize sidecar client
        
        Args:
            base_url: Sidecar service URL (e.g., "http://localhost:8001")
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    def request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> SidecarResponse:
        """
        Make HTTP request to sidecar service
        
        Args:
            endpoint: API endpoint (e.g., "/analyze")
            method: HTTP method
            data: Request payload
            timeout: Override default timeout
            
        Returns:
            SidecarResponse with success/failure status
        """
        url = f"{self.base_url}{endpoint}"
        request_timeout = timeout or self.timeout
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Sidecar request: {method} {url}")
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                timeout=request_timeout,
                headers={"Content-Type": "application/json"}
            )
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Success case
            if response.status_code == 200:
                logger.info(f"Sidecar success: {url} ({duration_ms:.0f}ms)")
                return SidecarResponse(
                    success=True,
                    data=response.json(),
                    error=None,
                    status_code=response.status_code,
                    duration_ms=duration_ms
                )
            
            # Error case (non-200)
            logger.warning(f"Sidecar error: {url} - Status {response.status_code}")
            return SidecarResponse(
                success=False,
                data=None,
                error=f"HTTP {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
                duration_ms=duration_ms
            )
        
        except requests.Timeout:
            # Timeout - graceful fallback
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Sidecar timeout: {url} ({duration_ms:.0f}ms)")
            return SidecarResponse(
                success=False,
                data=None,
                error=f"Request timed out after {request_timeout}s",
                status_code=None,
                duration_ms=duration_ms,
                timed_out=True
            )
        
        except requests.ConnectionError as e:
            # Connection failed - graceful fallback
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Sidecar connection error: {url} - {str(e)}")
            return SidecarResponse(
                success=False,
                data=None,
                error=f"Connection failed: {str(e)[:200]}",
                status_code=None,
                duration_ms=duration_ms
            )
        
        except Exception as e:
            # Unexpected error - graceful fallback
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.error(f"Sidecar unexpected error: {url} - {str(e)}")
            return SidecarResponse(
                success=False,
                data=None,
                error=f"Unexpected error: {str(e)[:200]}",
                status_code=None,
                duration_ms=duration_ms
            )
    
    def analyze_ticket(self, ticket_data: Dict[str, Any]) -> SidecarResponse:
        """
        Analyze ticket using sidecar service
        Convenience method for ticket analysis
        """
        return self.request(
            endpoint="/analyze",
            method="POST",
            data=ticket_data
        )
    
    def health_check(self) -> bool:
        """
        Check if sidecar service is reachable
        Returns True if healthy, False otherwise
        """
        try:
            response = self.request(
                endpoint="/health",
                method="GET",
                timeout=2.0
            )
            return response.success
        except Exception:
            return False