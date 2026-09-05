"""
E2E API Client Helper.
Supports both live HTTP server and in-process FastAPI TestClient.
"""

import os
from typing import Optional, Dict, Any
import httpx
from tests.e2e.helpers.contract_stubs import try_import


class E2EApiClient:
    """Client for testing FastAPI endpoints progressively."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("E2E_API_URL", "http://localhost:8000")
        self.app = None
        self.client = None
        
        # Check if live server is reachable
        self.is_live = False
        try:
            r = httpx.get(f"{self.base_url}/api/health", timeout=1.0)
            if r.status_code == 200:
                self.is_live = True
        except Exception:
            self.is_live = False

        if not self.is_live:
            # Fall back to in-process app if importable
            main_mod = try_import("backend.app.main")
            if main_mod and hasattr(main_mod, "app"):
                self.app = main_mod.app

    def is_available(self) -> bool:
        """Returns True if either live API or in-process FastAPI app is available."""
        return self.is_live or (self.app is not None)

    def get(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
        """Synchronous GET request."""
        if self.is_live:
            return httpx.get(f"{self.base_url}{endpoint}", headers=headers, timeout=5.0)
        elif self.app:
            from starlette.testclient import TestClient
            with TestClient(self.app) as c:
                return c.get(endpoint, headers=headers)
        raise RuntimeError("Neither live API nor FastAPI app is available.")

    def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, files: Optional[Any] = None, data: Optional[Any] = None) -> httpx.Response:
        """Synchronous POST request."""
        if self.is_live:
            return httpx.post(f"{self.base_url}{endpoint}", json=json, headers=headers, files=files, data=data, timeout=5.0)
        elif self.app:
            from starlette.testclient import TestClient
            with TestClient(self.app) as c:
                return c.post(endpoint, json=json, headers=headers, files=files, data=data)
        raise RuntimeError("Neither live API nor FastAPI app is available.")
