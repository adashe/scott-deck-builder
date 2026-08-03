"""Vercel serverless function — serves the deck builder's main page.

The app is open (no login). Every GET for the form page returns
templates/index.html directly.

(Access is expected to be gated at the platform level if needed — e.g. Vercel
Deployment Protection — rather than in application code.)
"""

import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

_INDEX_HTML_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "index.html"),
    "templates/index.html",
    os.path.join(os.getcwd(), "templates", "index.html"),
]


def _load_index_html() -> str:
    for path in _INDEX_HTML_CANDIDATES:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    raise RuntimeError("Could not find templates/index.html — checked: " + ", ".join(_INDEX_HTML_CANDIDATES))


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            body = _load_index_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            print("ERROR serving index:", traceback.format_exc(), file=sys.stderr)
            msg = b"Internal Server Error: could not load the deck builder page."
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
