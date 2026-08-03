"""Vercel serverless function — gates access to the deck builder's main page.

Every request for the form page goes through this function first:

  1. Valid session cookie                 -> serve templates/index.html
  2. No cookie, but a valid ?st= handoff  -> set the session cookie (now scoped
     token in the URL                         to THIS domain, vercel.app), strip
                                              the token via a 302 to "/", then
                                              the follow-up request hits case 1
  3. Neither                              -> friendly auth page (401) with
                                              Log in / Return buttons. No auto-
                                              redirect, so no login loop.

Why the ?st= path exists: the portal login runs on siscc-portal.com and this
app on vercel.app. A cookie minted by auth_callback while it runs under the
portal domain never reaches vercel.app. So auth_callback instead forwards a
short-lived handoff token in the URL, and THIS file — running on vercel.app —
turns it into the real cookie on the correct domain.
"""

import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.auth import (
    request_has_valid_session,
    get_handoff_token_from_path,
    verify_handoff_token,
    build_session_cookie_header,
    render_auth_error_page,
)

_INDEX_HTML_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "index.html"),
    "templates/index.html",
    os.path.join(os.getcwd(), "templates", "index.html"),
]

# Clean path to redirect to after consuming a handoff token (same origin,
# token stripped). Keep it relative so it stays on vercel.app.
CLEAN_APP_PATH = "/"


def _load_index_html() -> str:
    for path in _INDEX_HTML_CANDIDATES:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    raise RuntimeError("Could not find templates/index.html — checked: " + ", ".join(_INDEX_HTML_CANDIDATES))


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            # --- Case 1: already have a valid session cookie ---------------
            if request_has_valid_session(self.headers):
                return self._serve_index()

            # --- Case 2: no cookie yet, but a handoff token in the URL -----
            handoff = get_handoff_token_from_path(self.path)
            if handoff:
                user_id = verify_handoff_token(handoff)
                if user_id:
                    # Mint the session cookie on THIS domain, then redirect to a
                    # token-free URL so the token doesn't linger in history/bar.
                    self.send_response(302)
                    self.send_header("Location", CLEAN_APP_PATH)
                    self.send_header("Set-Cookie", build_session_cookie_header(user_id))
                    self.send_header("Referrer-Policy", "no-referrer")
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    return
                # Token present but invalid/expired -> fall through to the
                # friendly page (do NOT loop back to login automatically).

            # --- Case 3: no valid credential -> friendly terminal page -----
            return self._serve_auth_error(
                title="Session expired",
                message=(
                    "We couldn't verify your session for the Deck Builder. "
                    "Log in through the portal to continue."
                ),
            )

        except Exception:
            print("ERROR in page guard:", traceback.format_exc(), file=sys.stderr)
            return self._serve_auth_error(
                status=500,
                title="Something went wrong",
                message=(
                    "The Deck Builder hit an unexpected error while checking your "
                    "session. Please try logging in again."
                ),
            )

    # -- helpers ----------------------------------------------------------

    def _serve_index(self):
        body = _load_index_html().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _serve_auth_error(self, status: int = 401, title: str = "Session expired", message: str = ""):
        body = render_auth_error_page(title=title, message=message)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
