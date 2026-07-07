"""Vercel serverless function — /auth-callback

Handles the redirect from the portal after login:
  https://www.siscc-portal.com/scott-deck-builder/auth-callback?token=<supabase_access_token>

Flow:
  1. Read the token from the query string
  2. Verify its signature + expiry against SUPABASE_JWT_SECRET
  3. If valid: set this app's own httpOnly session cookie, then redirect
     (HTTP 302) to the form page with NO token in the URL
  4. If invalid/missing: redirect to the portal login page

The token never touches a cookie, localStorage, or any log line — it is
read once from the query string and discarded. The redirect in step 3 is
what "strips" it from the URL (the browser's address bar moves to the new,
token-free location).
"""

import os
import sys
import json
import traceback
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.auth import (
    verify_supabase_token,
    build_session_cookie_header,
    PORTAL_LOGIN_URL,
)

# Where to send the user after a successful login handoff.
# Must be the absolute Vercel URL so the browser stays on the same domain
# as the cookie (vercel.app). If we use a relative URL, the portal proxy
# resolves it to siscc-portal.com and the cookie never gets sent.
FORM_URL = "https://scott-deck-builder.vercel.app/"


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)
            token_values = query.get("token")
            token = token_values[0] if token_values else None

            if not token:
                return self._redirect_to_login()

            try:
                payload = verify_supabase_token(token)
            except ValueError as e:
                print(f"AUTH CALLBACK: token rejected — {e}", file=sys.stderr)
                return self._redirect_to_login()

            # Token is valid. Mint our own session cookie and send the user
            # to the form with the token no longer present in the URL.
            user_id = payload.get("sub", "unknown")
            cookie_header = build_session_cookie_header(user_id)

            self.send_response(302)
            self.send_header("Location", FORM_URL)
            self.send_header("Set-Cookie", cookie_header)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        except Exception:
            print("ERROR in /auth-callback:", traceback.format_exc(), file=sys.stderr)
            self._redirect_to_login()

    def _redirect_to_login(self):
        self.send_response(302)
        self.send_header("Location", PORTAL_LOGIN_URL)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
