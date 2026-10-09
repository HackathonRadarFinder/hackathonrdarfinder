"""Local mock website used by all tests (no real sites are contacted)."""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from collector_engine.config.loader import Settings

ROBOTS = """User-agent: *
Disallow: /private
"""

STATIC_PAGE = "<html><body><h1 id='t'>Hello static</h1><p class='q'>quote one</p></body></html>"

JS_PAGE = """<html><body><div id="c">loading...</div>
<script>setTimeout(() => {
  document.getElementById('c').innerHTML = '<p class="q">rendered by javascript</p>';
}, 300);</script></body></html>"""

LOAD_MORE_PAGE = """<html><body><div id="list"></div>
<button id="more">Load more</button>
<script>
let n = 0;
function add() { for (let i = 0; i < 3; i++) { n++; const d = document.createElement('div');
  d.className = 'item'; d.textContent = 'item ' + n; document.getElementById('list').appendChild(d); } }
add();
document.getElementById('more').onclick = () => { add(); if (n >= 9) document.getElementById('more').remove(); };
</script></body></html>"""

SCROLL_PAGE = """<html><body style="margin:0"><div id="list"></div>
<script>
let n = 0;
function add() { for (let i = 0; i < 3; i++) { n++; const d = document.createElement('div');
  d.className = 'item'; d.style.height = '600px'; d.textContent = 'scroll item ' + n;
  document.getElementById('list').appendChild(d); } }
add();
window.addEventListener('scroll', () => {
  if (n < 12 && window.innerHeight + window.scrollY >= document.body.scrollHeight - 50) add();
});
</script></body></html>"""

CAPTCHA_PAGE = "<html><body><div class='g-recaptcha'></div></body></html>"


class _Handler(BaseHTTPRequestHandler):
    hits: dict = {}

    def log_message(self, *args):  # silence
        pass

    def _send(self, status, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = self.path.split("?")[0]
        _Handler.hits[path] = _Handler.hits.get(path, 0) + 1
        n = _Handler.hits[path]
        if path == "/robots.txt":
            self._send(200, ROBOTS, "text/plain")
        elif path == "/ok":
            self._send(200, STATIC_PAGE)
        elif path == "/data.json":
            self._send(200, '{"items": [1, 2, 3]}', "application/json")
        elif path == "/private/secret":
            self._send(200, "secret")
        elif path == "/error500":
            self._send(500, "boom")
        elif path == "/flaky":  # fails twice, then succeeds
            self._send(503, "try later") if n <= 2 else self._send(200, STATIC_PAGE)
        elif path == "/notfound":
            self._send(404, "nope")
        elif path == "/forbidden":
            self._send(403, "denied")
        elif path == "/captcha":
            self._send(200, CAPTCHA_PAGE)
        elif path == "/js":
            self._send(200, JS_PAGE)
        elif path == "/loadmore":
            self._send(200, LOAD_MORE_PAGE)
        elif path == "/scroll":
            self._send(200, SCROLL_PAGE)
        elif path == "/list.json":
            self._send(200, '[{"a": 1}, {"a": 2}, {"a": 3}, {"a": 4}]', "application/json")
        elif path == "/headers":
            import json as _json

            self._send(200, _json.dumps({k: self.headers.get(k) for k in ("User-Agent", "Accept", "From")}), "application/json")
        elif path == "/ua":
            self._send(200, self.headers.get("User-Agent", ""))
        else:
            self._send(404, "unknown")


@pytest.fixture(scope="session")
def server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


@pytest.fixture(autouse=True)
def _reset_hits():
    _Handler.hits.clear()


@pytest.fixture
def hits():
    return _Handler.hits


def pytest_addoption(parser):
    parser.addoption("--headed", action="store_true", help="show the Playwright browser window")


@pytest.fixture
def settings(tmp_path, request):
    """Fast settings for tests: tiny delays, 3 attempts."""
    headed = request.config.getoption("--headed")
    return Settings(
        headless=not headed,
        slow_mo_ms=400 if headed else 0,  # watchable speed
        hold_seconds=4 if headed else 0,  # keep each window open 4s before closing
        user_agent="TestCollector/1.0 (+test)",
        min_delay=0.0,
        max_delay=0.0,
        max_attempts=3,
        backoff_base=0.0,
        request_timeout=15,
        raw_data_dir=tmp_path / "raw",
        log_dir=tmp_path / "logs",
    )
