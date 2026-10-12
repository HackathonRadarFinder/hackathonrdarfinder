"""Isolated HTTP fixtures; all test traffic is restricted to loopback."""
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from collector_engine.config.loader import Settings
from collector_engine.network import HttpTransport, URLPolicy

ROBOTS = "User-agent: *\nDisallow: /private\n"
STATIC_PAGE = "<html><body><h1 id='t'>Hello static</h1><p class='q'>quote one</p></body></html>"


class _Handler(BaseHTTPRequestHandler):
    hits = {}
    config = {}

    def log_message(self, *args):
        pass

    def _send(self, status, body, ctype="text/html; charset=utf-8", location=None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        if location:
            self.send_header("Location", location)
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        self.hits[path] = self.hits.get(path, 0) + 1
        if path == "/robots.txt":
            self._send(self.config.get("robots_status", 200), self.config.get("robots_body", ROBOTS),
                       "text/plain", self.config.get("robots_location"))
        elif path in ("/ok", "/private/secret"):
            self._send(200, STATIC_PAGE)
        elif path == "/data.json":
            self._send(200, '{"items": [1, 2, 3]}', "application/json")
        elif path == "/list.json":
            self._send(200, "[1, 2, 3, 4]", "application/json")
        elif path == "/error500":
            self._send(500, "boom")
        elif path == "/flaky":
            self._send(503, "try later") if self.hits[path] <= 2 else self._send(200, STATIC_PAGE)
        elif path == "/forbidden":
            self._send(403, "denied")
        elif path == "/throttled":
            self._send(429, "slow down")
        elif path == "/captcha":
            self._send(200, "<div class='g-recaptcha'></div>")
        elif path == "/headers":
            self._send(200, json.dumps({k: self.headers.get(k) for k in ("User-Agent", "Accept", "From")}),
                       "application/json")
        elif path == "/ua":
            self._send(200, self.headers.get("User-Agent", ""))
        elif path == "/redirect-ok":
            self._send(302, "", location="/ok")
        elif path == "/redirect-private":
            self._send(302, "", location="/private/secret")
        elif path == "/redirect-outside":
            self._send(302, "", location=self.config["outside_url"])
        elif path == "/redirect-loop":
            self._send(302, "", location="/redirect-loop")
        elif path == "/oversized":
            self._send(200, "x" * 8192)
        elif path == "/oversized-no-length":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            try:
                self.wfile.write(b"x" * 8192)
            except (BrokenPipeError, ConnectionResetError):
                pass
        else:
            self._send(404, "not found")


@pytest.fixture(autouse=True)
def _loopback_only_network(monkeypatch):
    """Fail before any accidental connection to an external destination."""
    original = socket.socket.connect

    def connect(sock, address):
        assert address[0] in ("127.0.0.1", "::1"), "tests must never contact external hosts"
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)
    _Handler.hits.clear()
    _Handler.config.clear()


@pytest.fixture(scope="session")
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()
    worker.join(timeout=5)


@pytest.fixture
def hits():
    return _Handler.hits


@pytest.fixture
def server_config():
    return _Handler.config


@pytest.fixture
def settings(tmp_path):
    return Settings(user_agent="TestCollector/1.0 (+test)", min_delay=0.0, max_delay=0.0,
                    max_attempts=3, backoff_base=0.0, request_timeout=2,
                    raw_data_dir=tmp_path / "raw", log_dir=tmp_path / "logs")


@pytest.fixture
def transport(server, settings):
    return HttpTransport(URLPolicy([server], allow_loopback=True), timeout=settings.request_timeout,
                         max_bytes=settings.max_response_bytes, max_redirects=settings.max_redirects)
