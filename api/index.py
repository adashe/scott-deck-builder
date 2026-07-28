"""Vercel serverless function — gates access to the deck builder's main page.

This replaces static serving of public/index.html (now at templates/index.html). Instead, every request
for the form page goes through this function first:

  - Valid session cookie  -> serve index.html
  - No/invalid cookie     -> 302 redirect to the portal login page

This is what makes direct hits to scott-deck-builder.vercel.app/ (bypassing
the portal entirely) redirect to login instead of just showing the form.
"""

import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.auth import request_has_valid_session, PORTAL_LOGIN_URL

TEST_URL_A = "https://www.reddit.com"
TEST_URL_B = "https://www.washingtonpost.com"

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
            if not request_has_valid_session(self.headers):
                self.send_response(302)
                self.send_header("Location", TEST_URL_A)
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return

            html = _load_index_html()
            body = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        except Exception:
            print("ERROR in page guard:", traceback.format_exc(), file=sys.stderr)
            self.send_response(302)
            self.send_header("Location", TEST_URL_B)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
