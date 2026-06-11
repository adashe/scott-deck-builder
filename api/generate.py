"""Vercel serverless function — /api/generate
 
Receives a multipart/form-data POST:
  - meta:               JSON-encoded form metadata (customer info, value drivers, etc.)
  - customerLogo:       (optional) the customer logo file
  - proposalImage_N:    (optional) image for proposal slide N
 
Generates:
  - SCOTT_{Customer}_Deck.pptx
  - SCOTT_{Customer}_Script.docx
 
Uploads both files as a zip to Vercel Blob storage and returns a JSON
redirect URL so the browser can download it directly — avoiding the
4.5 MB serverless response payload limit.
 
Vercel Blob setup (one-time, in the Vercel dashboard):
  1. Go to your project → Storage → Create Database → Blob
  2. Link it to this project
  3. Vercel automatically sets the BLOB_READ_WRITE_TOKEN env variable
"""
 
import os
import io
import sys
import json
import zipfile
import tempfile
import traceback
import urllib.request
import urllib.error
import cgi
from http.server import BaseHTTPRequestHandler
from pathlib import Path
 
# Add parent dir to path so we can import lib/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
 
from lib.deck_builder import build_deck
from lib.script_builder import build_script
 
 
# ---------------------------------------------------------------------------
# Template location helper
# ---------------------------------------------------------------------------
 
def _find_template() -> str:
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "templates", "source_deck.pptx"),
        "templates/source_deck.pptx",
        os.path.join(os.getcwd(), "templates", "source_deck.pptx"),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise RuntimeError(
        "Could not find templates/source_deck.pptx — checked: " + ", ".join(candidates)
    )
 
 
def _safe_filename(name: str) -> str:
    """Convert a customer name into a filesystem-safe string."""
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in (name or "Customer"))
    return safe.strip("_") or "Customer"
 
 
# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
 
def _generate(meta: dict, customer_logo_path: str | None, proposal_image_paths: dict, out_dir: str) -> tuple[str, str]:
    """Build the deck and script in out_dir. Returns (deck_path, script_path)."""
    template_path = _find_template()
    customer = _safe_filename(meta.get("customerName", ""))
    deck_path = os.path.join(out_dir, f"SCOTT_{customer}_Deck.pptx")
    script_path = os.path.join(out_dir, f"SCOTT_{customer}_Script.docx")
 
    build_deck(template_path, deck_path, meta, customer_logo_path, proposal_image_paths)
    build_script(meta, script_path)
    return deck_path, script_path
 
 
def _zip_outputs(deck_path: str, script_path: str) -> bytes:
    """Bundle the two output files into a zip and return the bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(deck_path, arcname=os.path.basename(deck_path))
        z.write(script_path, arcname=os.path.basename(script_path))
    return buf.getvalue()
 
 
# ---------------------------------------------------------------------------
# Vercel Blob upload
# ---------------------------------------------------------------------------
 
def _upload_to_blob(zip_bytes: bytes, filename: str) -> str:
    """Upload zip_bytes to Vercel Blob and return the public download URL.
 
    Uses the Vercel Blob REST API directly (no SDK needed — stdlib only).
    Requires the BLOB_READ_WRITE_TOKEN environment variable, which Vercel sets
    automatically when you link a Blob store to the project.
 
    Docs: https://vercel.com/docs/storage/vercel-blob/using-blob-sdk#upload-a-file
    """
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")

    if not token:
        raise RuntimeError(
            "BLOB_READ_WRITE_TOKEN is not set. "
            "Link a Vercel Blob store to this project in the Vercel dashboard "
            "(Storage → Create Database → Blob), then redeploy."
        )
 
    # PUT to the Vercel Blob API
    api_url = f"https://blob.vercel-storage.com/{filename}?access=public"
    req = urllib.request.Request(
        api_url,
        data=zip_bytes,
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/zip",
            # access=public makes the URL directly downloadable by the browser
            "x-api-version": "7",
        },
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
 
    # The API returns { url, downloadUrl, pathname, contentType, ... }
    download_url = result.get("downloadUrl") or result.get("url")
    if not download_url:
        raise RuntimeError(f"Blob API returned unexpected response: {result}")
    return download_url
 
 
# ---------------------------------------------------------------------------
# Serverless handler
# ---------------------------------------------------------------------------
 
class handler(BaseHTTPRequestHandler):
 
    def do_OPTIONS(self):
        """CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
 
    def do_GET(self):
        """Friendly message if someone visits /api/generate in a browser."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SCOTT Automation Deck Builder API. POST a multipart form to this endpoint.")
 
    def do_POST(self):
        try:
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                return self._send_error(400, "Expected multipart/form-data request")
 
            environ = {
                "REQUEST_METHOD": "POST",
                "CONTENT_TYPE": content_type,
                "CONTENT_LENGTH": self.headers.get("Content-Length", "0"),
            }
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ=environ,
                keep_blank_values=True,
            )
 
            # --- Parse meta JSON ---
            meta_field = form.getvalue("meta")
            if not meta_field:
                return self._send_error(400, "Missing 'meta' field in form data")
            try:
                meta = json.loads(meta_field)
            except json.JSONDecodeError as e:
                return self._send_error(400, f"Invalid JSON in meta: {e}")
 
            with tempfile.TemporaryDirectory() as tmp:
                upload_dir = os.path.join(tmp, "uploads")
                os.makedirs(upload_dir, exist_ok=True)
 
                # --- Customer logo ---
                customer_logo_path = None
                if "customerLogo" in form and form["customerLogo"].filename:
                    customer_logo_path = self._save_upload(form["customerLogo"], upload_dir, "customer_logo")
 
                # --- Proposal images ---
                proposal_image_paths = {}
                for key in form.keys():
                    if key.startswith("proposalImage_"):
                        try:
                            idx = int(key.split("_", 1)[1])
                        except ValueError:
                            continue
                        if form[key].filename:
                            saved = self._save_upload(form[key], upload_dir, f"proposal_{idx}")
                            proposal_image_paths[idx] = saved
 
                # --- Generate deck + script ---
                out_dir = os.path.join(tmp, "out")
                os.makedirs(out_dir, exist_ok=True)
                deck_path, script_path = _generate(meta, customer_logo_path, proposal_image_paths, out_dir)
                zip_bytes = _zip_outputs(deck_path, script_path)
 
                customer = _safe_filename(meta.get("customerName", ""))
                filename = f"SCOTT_{customer}_Deck_Bundle.zip"
 
                # --- Upload to Vercel Blob; return download URL ---
                # This sidesteps the 4.5 MB serverless response payload limit.
                download_url = _upload_to_blob(zip_bytes, filename)
 
                body = json.dumps({"downloadUrl": download_url}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)
 
        except Exception as e:
            print("ERROR in /api/generate:", traceback.format_exc(), file=sys.stderr)
            return self._send_error(500, f"Server error: {e}")
 
    def _save_upload(self, field, upload_dir: str, basename: str) -> str:
        """Save an uploaded file field to disk; return the path."""
        ext = os.path.splitext(field.filename)[1].lower() or ".bin"
        out_path = os.path.join(upload_dir, f"{basename}{ext}")
        with open(out_path, "wb") as f:
            data = field.file.read() if hasattr(field, "file") and field.file else field.value
            if isinstance(data, str):
                data = data.encode("latin-1")
            f.write(data)
        return out_path
 
    def _send_error(self, code: int, message: str):
        body = json.dumps({"error": message}).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)