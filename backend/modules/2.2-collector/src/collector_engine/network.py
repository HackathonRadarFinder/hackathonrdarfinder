"""Bounded HTTP GET transport with explicit origins and pinned, validated addresses.

No proxies, cookies, automatic redirects or credential discovery are used. Tests
may explicitly permit loopback on an injected policy; normal policies require
every resolved address to be globally routable.
"""
from __future__ import annotations

import http.client
import ipaddress
import re
import socket
import ssl
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

from .models import PermanentFetchError, TemporaryFetchError


def parsed_url(url: str):
    if not isinstance(url, str) or not url or any(ord(c) < 33 or ord(c) == 127 for c in url):
        raise PermanentFetchError("URL must be a nonempty HTTP(S) URL without whitespace or controls")
    try:
        parts = urlsplit(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError
        if parts.username is not None or parts.password is not None:
            raise PermanentFetchError("URL credentials are not allowed")
        host = parts.hostname.encode("idna").decode("ascii").lower()
        if not host or host.endswith(".") or "%" in host or "\\" in host:
            raise ValueError
        port = parts.port if parts.port is not None else (443 if parts.scheme == "https" else 80)
        if not 1 <= port <= 65535:
            raise ValueError
    except (ValueError, UnicodeError):
        raise PermanentFetchError("Invalid HTTP(S) URL") from None
    return parts, host, port


def origin_for_url(url: str) -> str:
    parts, host, port = parsed_url(url)
    authority = f"[{host}]" if ":" in host else host
    return f"{parts.scheme}://{authority}:{port}"


def safe_url(url: str) -> str:
    """Never include user information, query values, fragments or log controls."""
    try:
        parts = urlsplit(url)
        host = parts.hostname or "invalid"
        authority = f"[{host}]" if ":" in host else host
        if parts.port:
            authority += f":{parts.port}"
        return urlunsplit((parts.scheme, authority, quote(parts.path, safe="/%:@-._~"), "", ""))
    except (ValueError, TypeError):
        return "[invalid URL]"


class URLPolicy:
    def __init__(self, allowed_origins, allow_loopback: bool = False, resolver=None):
        if type(allow_loopback) is not bool:
            raise ValueError("allow_loopback must be a boolean")
        self.allowed_origins = frozenset(origin_for_url(value) for value in allowed_origins)
        if not self.allowed_origins:
            raise ValueError("At least one allowed origin is required")
        self.allow_loopback = allow_loopback
        self.resolver = resolver or socket.getaddrinfo

    def resolve(self, url: str):
        parts, host, port = parsed_url(url)
        if origin_for_url(url) not in self.allowed_origins:
            raise PermanentFetchError("URL origin is not explicitly allowed")
        try:
            addresses = self.resolver(host, port, type=socket.SOCK_STREAM)
        except OSError:
            raise TemporaryFetchError("Unable to resolve permitted host") from None
        if not addresses:
            raise TemporaryFetchError("Permitted host resolved to no addresses")
        for family, socktype, proto, _canon, sockaddr in addresses:
            if family not in (socket.AF_INET, socket.AF_INET6) or socktype != socket.SOCK_STREAM:
                raise PermanentFetchError("Unsupported network address")
            address = ipaddress.ip_address(sockaddr[0])
            address = address.ipv4_mapped or address if isinstance(address, ipaddress.IPv6Address) else address
            if not (address.is_global or (self.allow_loopback and address.is_loopback)):
                raise PermanentFetchError("Private, local or reserved network destinations are forbidden")
        return parts, host, port, addresses


def _connect_address(address, timeout):
    family, socktype, proto, _canon, sockaddr = address
    sock = socket.socket(family, socktype, proto)
    try:
        sock.settimeout(timeout)
        sock.connect(sockaddr)  # The already validated numeric address: no second DNS lookup.
        return sock
    except BaseException:
        sock.close()
        raise


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host, port, address, timeout):
        super().__init__(host, port, timeout=timeout)
        self._address = address

    def connect(self):
        self.sock = _connect_address(self._address, self.timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, port, address, timeout):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._address = address

    def connect(self):
        sock = _connect_address(self._address, self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


@dataclass(frozen=True)
class HTTPResponse:
    status: int
    body: bytes
    headers: dict[str, str]
    url: str

    @property
    def text(self):
        match = re.search(r"charset\s*=\s*[\"']?([^;\s\"']+)", self.headers.get("content-type", ""), re.I)
        encoding = match.group(1) if match else "utf-8"
        try:
            return self.body.decode(encoding, "replace")
        except LookupError:
            return self.body.decode("utf-8", "replace")


class HttpTransport:
    def __init__(self, policy: URLPolicy, timeout=30, max_bytes=2_000_000,
                 max_redirects=5, before_request: Callable[[str], None] | None = None,
                 max_job_seconds=120):
        import math
        if not math.isfinite(timeout) or not 0 < timeout <= 120:
            raise ValueError("timeout must be finite and in (0, 120]")
        if type(max_bytes) is not int or not 1 <= max_bytes <= 10_000_000:
            raise ValueError("max_bytes must be between 1 and 10000000")
        if type(max_redirects) is not int or not 0 <= max_redirects <= 10:
            raise ValueError("max_redirects must be between 0 and 10")
        if not math.isfinite(max_job_seconds) or not 0 < max_job_seconds <= 600:
            raise ValueError("max_job_seconds must be finite and in (0, 600]")
        self.policy, self.timeout = policy, timeout
        self.max_bytes, self.max_redirects = max_bytes, max_redirects
        self.before_request = before_request
        self.max_job_seconds = max_job_seconds
        self.deadline = None

    def _remaining(self):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise PermanentFetchError("Collection time budget exhausted")
        return min(self.timeout, remaining)

    @contextmanager
    def budget(self):
        """Share a deadline across robots requests, content and manager retries."""
        outer = self.deadline is None
        if outer:
            self.deadline = time.monotonic() + self.max_job_seconds
        try:
            yield
        finally:
            if outer:
                self.deadline = None

    def request(self, url: str, headers=None, authorize=None) -> HTTPResponse:
        with self.budget():
            return self._request(url, headers or {}, authorize)

    def _request(self, url, headers, authorize):
        safe_headers = {"Accept-Encoding": "identity", "Connection": "close"}
        for key, value in headers.items():
            if key.lower() in {"authorization", "proxy-authorization", "cookie", "host", "content-length", "transfer-encoding"}:
                raise PermanentFetchError("Sensitive or framing request headers are forbidden")
            if not re.fullmatch(r"[A-Za-z0-9-]+", key) or not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise PermanentFetchError("Invalid request header")
            safe_headers[key] = value
        current = url
        for redirect in range(self.max_redirects + 1):
            self._remaining()
            parts, host, port, addresses = self.policy.resolve(current)
            if authorize is not None:
                authorize(current)  # Must happen BEFORE the content request, including every redirect.
            if self.before_request is not None:
                self.before_request(current)
            timeout = self._remaining()
            cls = _PinnedHTTPSConnection if parts.scheme == "https" else _PinnedHTTPConnection
            connection = cls(host, port, addresses[0], timeout)
            try:
                target = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
                connection.request("GET", target, headers=safe_headers)
                response = connection.getresponse()
                response_headers = {key.lower(): value for key, value in response.getheaders()}
                if response.status in (301, 302, 303, 307, 308):
                    location = response_headers.get("location")
                    if not location or redirect >= self.max_redirects:
                        raise PermanentFetchError("Invalid redirect or redirect limit reached")
                    current = urljoin(current, location)
                    continue
                if response_headers.get("content-encoding", "identity").lower() not in ("", "identity"):
                    raise PermanentFetchError("Compressed responses are not supported by bounded transport")
                length = response_headers.get("content-length")
                if length is not None:
                    try:
                        size = int(length)
                    except ValueError:
                        raise PermanentFetchError("Invalid response Content-Length") from None
                    if size < 0 or size > self.max_bytes:
                        raise PermanentFetchError("Response exceeds configured byte limit")
                chunks, total = [], 0
                while True:
                    if connection.sock is not None:
                        connection.sock.settimeout(self._remaining())
                    chunk = response.read1(min(65536, self.max_bytes + 1 - total))
                    self._remaining()
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise PermanentFetchError("Response exceeds configured byte limit")
                return HTTPResponse(response.status, b"".join(chunks), response_headers, current)
            except (OSError, http.client.HTTPException) as exc:
                raise TemporaryFetchError(f"HTTP transport failed ({type(exc).__name__})") from None
            finally:
                connection.close()
        raise PermanentFetchError("Redirect limit reached")
