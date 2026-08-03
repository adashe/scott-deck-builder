import os, sys, io, time, json, hmac, hashlib, base64
from urllib.parse import urlparse, parse_qs

os.environ["SUPABASE_JWT_SECRET"] = "supabase_secret_for_test"
os.environ["SESSION_SECRET"] = "app_session_secret_for_test"
sys.path.insert(0, ".")

import importlib
import lib.auth as auth
importlib.reload(auth)

def b64url(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def make_supabase_token(secret, sub="user-123", exp_delta=3600, alg="HS256"):
    hdr = {"alg": alg, "typ": "JWT"}
    pay = {"sub": sub, "exp": int(time.time())+exp_delta, "iss": "supabase", "role": "authenticated"}
    h = b64url(json.dumps(hdr).encode()); p = b64url(json.dumps(pay).encode())
    sig = hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{b64url(sig)}"

# --- Fake handler driver ----------------------------------------------------
class Rec:
    def __init__(self, path, cookie=None):
        self.path = path
        self.headers = {"Cookie": cookie} if cookie else {}
        self.status = None; self.sent = {}; self.wfile = io.BytesIO()
    # patched HTTP methods
    def send_response(self, code): self.status = code
    def send_header(self, k, v): self.sent.setdefault(k, []).append(v)
    def end_headers(self): pass

def drive(handler_cls, path, cookie=None):
    inst = handler_cls.__new__(handler_cls)
    rec = Rec(path, cookie)
    for attr in ("path","headers"): setattr(inst, attr, getattr(rec, attr))
    inst.send_response = rec.send_response
    inst.send_header = rec.send_header
    inst.end_headers = rec.end_headers
    inst.wfile = rec.wfile
    inst.do_GET()
    rec.body = rec.wfile.getvalue()
    return rec

import api.auth_callback as cb; importlib.reload(cb)
import api.index as idx; importlib.reload(idx)

def loc(rec): return (rec.sent.get("Location") or [None])[0]
def setcookie(rec): return (rec.sent.get("Set-Cookie") or [None])[0]

print("="*70)
print("TEST 1: valid Supabase token -> auth_callback redirects to vercel with ?st=")
tok = make_supabase_token(os.environ["SUPABASE_JWT_SECRET"])
r = drive(cb.handler, f"/auth-callback?token={tok}")
assert r.status == 302, r.status
L = loc(r); print("  status 302, Location:", L[:60], "...")
assert L.startswith("https://scott-deck-builder.vercel.app/?st="), L
assert setcookie(r) is None, "auth_callback must NOT set a cookie (wrong domain)"
assert "no-referrer" in (r.sent.get("Referrer-Policy") or [""])[0]
handoff = parse_qs(urlparse(L).query)["st"][0]
print("  PASS — no cookie set here, handoff token issued")

print("="*70)
print("TEST 2: index.py receives ?st=<handoff> -> sets cookie + strips token")
r2 = drive(idx.handler, f"/?st={handoff}")
assert r2.status == 302, r2.status
assert loc(r2) == "/", loc(r2)
sc = setcookie(r2); print("  Set-Cookie:", sc[:55], "...")
assert sc and sc.startswith("scott_deck_session="), sc
assert "HttpOnly" in sc and "Secure" in sc and "SameSite=Lax" in sc
cookie_val = sc.split(";")[0].split("=",1)[1]
print("  PASS — cookie minted on vercel.app, redirect to clean '/'")

print("="*70)
print("TEST 3: follow-up request WITH cookie -> serves the form page (200)")
r3 = drive(idx.handler, "/", cookie=f"scott_deck_session={cookie_val}")
assert r3.status == 200, r3.status
assert b"<!DOCTYPE html" in r3.body or b"<html" in r3.body.lower(), r3.body[:80]
print("  status 200, body bytes:", len(r3.body), "-> PASS")

print("="*70)
print("TEST 4: no cookie, no token -> friendly 401 page (NO auto-redirect)")
r4 = drive(idx.handler, "/")
assert r4.status == 401, r4.status
assert loc(r4) is None, "must not redirect (breaks the loop)"
assert b"Log in" in r4.body and b"Return to main app" in r4.body
print("  status 401, has Login + Return buttons, no Location -> PASS")

print("="*70)
print("TEST 5: expired handoff token -> falls through to friendly 401")
expired = auth._sign({"sub":"u","typ":"handoff","iat":int(time.time())-999,"exp":int(time.time())-1})
r5 = drive(idx.handler, f"/?st={expired}")
assert r5.status == 401 and loc(r5) is None, (r5.status, loc(r5))
print("  PASS")

print("="*70)
print("TEST 6: handoff token cannot be replayed as a session cookie, and")
print("        a session token cannot be used as a handoff token (typ enforced)")
assert auth.verify_session_cookie_value(handoff) is False, "handoff must not pass as session!"
sess = auth.create_session_cookie_value("u")
assert auth.verify_handoff_token(sess) is None, "session must not pass as handoff!"
print("  PASS — token types are not interchangeable")

print("="*70)
print("TEST 7: bad Supabase signature -> friendly page, no redirect to vercel")
badtok = make_supabase_token("WRONG_SECRET")
r7 = drive(cb.handler, f"/auth-callback?token={badtok}")
assert r7.status == 401, r7.status
assert loc(r7) is None
assert b"rejected" in r7.body.lower() or b"verified" in r7.body.lower()
print("  status 401 friendly page -> PASS")

print("="*70)
print("TEST 8: missing token at auth_callback -> friendly 'Not signed in' page")
r8 = drive(cb.handler, "/auth-callback")
assert r8.status == 401 and loc(r8) is None
print("  PASS")

print("="*70)
print("TEST 9: tampered cookie signature rejected")
tampered = cookie_val[:-4] + ("AAAA" if not cookie_val.endswith("AAAA") else "BBBB")
r9 = drive(idx.handler, "/", cookie=f"scott_deck_session={tampered}")
assert r9.status == 401, r9.status
print("  PASS")

print("\nALL TESTS PASSED ✔")
