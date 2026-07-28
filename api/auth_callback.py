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
    PORTAL_LOGIN_URL
)

TEST_URL_1 = "https://www.youtube.com"
TEST_URL_2 = "https://www.nytimes.com"
TEST_URL_3 = "https://www.github.com"

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
                return self._redirect_to_login_1()

            try:
                payload = verify_supabase_token(token)

            except ValueError as e:
                # Log enough detail to diagnose without exposing the token itself
                import base64, json as _json

                try:

                    parts = token.split(".")

                    if len(parts) == 3:
                        pad = lambda s: s + "=" * (-len(s) % 4)
                        hdr = _json.loads(base64.urlsafe_b64decode(pad(parts[0])))
                        pay = _json.loads(base64.urlsafe_b64decode(pad(parts[1])))
                        print(f"AUTH CALLBACK: token rejected — {e}", file=sys.stderr)
                        print(f"AUTH CALLBACK: token header alg={hdr.get('alg')}, typ={hdr.get('typ')}", file=sys.stderr)
                        print(f"AUTH CALLBACK: token payload iss={pay.get('iss')}, aud={pay.get('aud')}, role={pay.get('role')}", file=sys.stderr)
                        import time
                        exp = pay.get("exp")
                        print(f"AUTH CALLBACK: token exp={exp}, now={int(time.time())}, expired={exp and time.time() >= float(exp)}", file=sys.stderr)
                        secret = os.environ.get("SUPABASE_JWT_SECRET", "")
                        print(f"AUTH CALLBACK: SUPABASE_JWT_SECRET present={bool(secret)}, length={len(secret)}", file=sys.stderr)

                except Exception as diag_err:
                    print(f"AUTH CALLBACK: token rejected — {e} (diagnostic also failed: {diag_err})", file=sys.stderr)
                return self._redirect_to_login_2()

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
            self._redirect_to_login_3()

    # def _redirect_to_login(self):
    #     self.send_response(302)
    #     self.send_header("Location", PORTAL_LOGIN_URL)
    #     self.send_header("Cache-Control", "no-store")
    #     self.end_headers()

    def _redirect_to_login_1(self):
        self.send_response(302)
        self.send_header("Location", TEST_URL_1)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _redirect_to_login_2(self):
        self.send_response(302)
        self.send_header("Location", TEST_URL_2)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _redirect_to_login_3(self):
        self.send_response(302)
        self.send_header("Location", TEST_URL_3)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()