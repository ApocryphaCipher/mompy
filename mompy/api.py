"""A small client for DOSBox Staging's web API (standard library only).

Only what mompy needs: the version, memory reads, and memory writes with a compare-and-swap.
See ``docs/reference/dosbox-api.md`` for how each request behaves and where that was checked.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request

DEFAULT_URL = "http://127.0.0.1:8086"
MEMORY_SIZE = 16 * 1024 * 1024  # DOSBox's emulated memory


class ApiError(Exception):
    """The server could not be reached, or answered something unexpected."""


class WritesDisabled(ApiError):
    """HTTP 403: the server refuses state-changing requests (the research fork's gate)."""


class Mismatch(ApiError):
    """HTTP 412: the bytes were not what the compare-and-swap expected; nothing was written."""

    def __init__(self, message: str, current: bytes | None = None):
        super().__init__(message)
        self.current = current


class DosboxApi:
    def __init__(self, url: str = DEFAULT_URL, timeout: float = 30.0):
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _request(self, path: str, method: str = "GET", data: bytes | None = None,
                 headers: dict | None = None) -> bytes:
        req = urllib.request.Request(f"{self.url}/api/v1{path}", data=data, method=method,
                                     headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return res.read()
        except urllib.error.HTTPError as err:
            try:
                body = err.read()
            finally:
                err.close()
            if err.code == 403:
                raise WritesDisabled(_message(body) or "forbidden") from None
            if err.code == 412:
                raise Mismatch("the memory is not what was expected", _current_bytes(body)) from None
            raise ApiError(f"HTTP {err.code} for {method} {path}: {_message(body)}") from None
        except (urllib.error.URLError, OSError) as err:
            raise ApiError(f"cannot reach {self.url}: {getattr(err, 'reason', err)}") from None

    def info(self) -> dict:
        """``GET /dosbox/info``: ``version``, ``configHome`` and ``configWebserver``."""
        try:
            return json.loads(self._request("/dosbox/info"))
        except json.JSONDecodeError:
            raise ApiError("the server did not answer with JSON: is this DOSBox's web API?") from None

    def read(self, address: int, length: int) -> bytes:
        """``length`` bytes from the linear ``address``."""
        data = self._request(f"/memory/{address}/{length}")
        if len(data) != length:
            raise ApiError(f"asked for {length} bytes at {address:#x}, got {len(data)}")
        return data

    def write(self, address: int, data: bytes, expect: bytes) -> None:
        """Write ``data`` at ``address`` only if the memory there is ``expect`` right now.

        Raises ``Mismatch`` (nothing written) if it is not, ``WritesDisabled`` if the server refuses.
        """
        if len(data) != len(expect):
            raise ValueError("data and expect must be the same length")
        etag = '"' + base64.b64encode(expect).decode() + '"'
        self._request(f"/memory/{address}", method="PUT", data=data,
                      headers={"Content-Type": "application/octet-stream", "If-Match": etag})


def _message(body: bytes) -> str:
    try:
        parsed = json.loads(body)
        return str(parsed.get("error", "")) if isinstance(parsed, dict) else ""
    except (json.JSONDecodeError, UnicodeDecodeError):
        return body.decode("utf-8", "replace").strip()[:200]


def _current_bytes(body: bytes) -> bytes | None:
    """The 412 answer carries the bytes that are really there: ``{"memory": {"addr": ..., "data": <base64>}}``
    (as DOSBox Staging 0.83.0 answers; checked 2026-10-13)."""
    try:
        parsed = json.loads(body)
        return base64.b64decode(parsed["memory"]["data"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None
