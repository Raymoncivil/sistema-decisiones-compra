"""HTTP client for the Sistema de Decisiones de Compra API."""
from __future__ import annotations

from pathlib import Path

import httpx

DEFAULT_BASE_URL = "http://localhost:8000"


class APIError(Exception):
    """Raised when the API returns a non-2xx response."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class APIClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 120.0) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=timeout)

    # ------------------------------------------------------------------

    def analyze(self, csv_path: Path | str) -> dict:
        """POST /analizar — upload a CSV and return the JSON response dict."""
        csv_path = Path(csv_path)
        with csv_path.open("rb") as f:
            response = self._client.post(
                "/analizar",
                files={"archivo": (csv_path.name, f, "text/csv")},
            )
        _raise_for_status(response)
        return response.json()

    def analyze_bytes(self, csv_bytes: bytes, filename: str = "data.csv") -> dict:
        """POST /analizar — upload raw CSV bytes and return the JSON response dict."""
        response = self._client.post(
            "/analizar",
            files={"archivo": (filename, csv_bytes, "text/csv")},
        )
        _raise_for_status(response)
        return response.json()

    def download_pdf(self, reporte_id: str) -> bytes:
        """GET /reporte/{reporte_id} — return raw PDF bytes."""
        response = self._client.get(f"/reporte/{reporte_id}")
        _raise_for_status(response)
        return response.content

    def close(self) -> None:
        self._client.close()

    # context-manager support
    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()


# ── helpers ───────────────────────────────────────────────────────────────────

def _raise_for_status(response: httpx.Response) -> None:
    if response.is_error:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise APIError(response.status_code, detail)
