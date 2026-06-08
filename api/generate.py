"""Vercel serverless function — /api/generate

Receives a multipart/form-data POST:
  - meta:               JSON-encoded form metadata (customer info, value drivers, etc.)
  - customerLogo:       (optional) the customer logo file
  - proposalImage_N:    (optional) image for proposal slide N

Generates:
  - SCOTT_{Customer}_Deck.pptx
  - SCOTT_{Customer}_Script.docx

Returns a zip containing both files.
"""

import os
import io
import sys
import json
import zipfile
import tempfile
import traceback
import cgi
from http.server import BaseHTTPRequestHandler
from pathlib import Path

# Add parent dir to path so we can import lib/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.deck_builder import build_deck
from lib.script_builder import build_script


# Find the template — Vercel places includeFiles next to the function
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
    """Convert a customer name into a filesystem-safe string for the output filename."""
    safe = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in (name or "Customer"))
    return safe.strip("_") or "Customer"


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
    """Bundle the two output files into a single zip and return the bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(deck_path, arcname=os.path.basename(deck_path))
        z.write(script_path, arcname=os.path.basename(script_path))
    return buf.getvalue()


class handler(BaseHTTPRequestHandler):

    def do_OPTIONS(self):
        """CORS preflight — useful if hosting frontend on a different domain."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Friendly response if someone hits /api/generate in their browser."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"SCOTT Automation Deck Builder API. POST a multipart form to this endpoint.")

    def do_POST(self):
        try:
            # Parse multipart/form-data
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                return self._send_error(400, "Expected multipart/form-data request")

            # Use cgi.FieldStorage to parse multipart (stdlib, works on Vercel)
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

            # Read the meta JSON
            meta_field = form.getvalue("meta")
            if not meta_field:
                return self._send_error(400, "Missing 'meta' field in form data")
            try:
                meta = json.loads(meta_field)
            except json.JSONDecodeError as e:
                return self._send_error(400, f"Invalid JSON in meta: {e}")

            # Write uploaded files to a temp directory
            with tempfile.TemporaryDirectory() as tmp:
                upload_dir = os.path.join(tmp, "uploads")
                os.makedirs(upload_dir, exist_ok=True)

                # Customer logo
                customer_logo_path = None
                if "customerLogo" in form and form["customerLogo"].filename:
                    customer_logo_path = self._save_upload(form["customerLogo"], upload_dir, "customer_logo")

                # Proposal images (keyed by proposalImage_0, proposalImage_1, ...)
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

                # Generate the deck + script
                out_dir = os.path.join(tmp, "out")
                os.makedirs(out_dir, exist_ok=True)
                deck_path, script_path = _generate(meta, customer_logo_path, proposal_image_paths, out_dir)
                zip_bytes = _zip_outputs(deck_path, script_path)

                customer = _safe_filename(meta.get("customerName", ""))
                filename = f"SCOTT_{customer}_Deck_Bundle.zip"

                # Send the zip back
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(len(zip_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(zip_bytes)

        except Exception as e:
            # Log full traceback to Vercel logs for debugging
            print("ERROR in /api/generate:", traceback.format_exc(), file=sys.stderr)
            return self._send_error(500, f"Server error: {e}")

    def _save_upload(self, field, upload_dir: str, basename: str) -> str:
        """Save an uploaded file from a cgi.FieldStorage entry to disk; return the path."""
        # Preserve the original extension
        ext = os.path.splitext(field.filename)[1].lower() or ".bin"
        out_path = os.path.join(upload_dir, f"{basename}{ext}")
        with open(out_path, "wb") as f:
            # field.file is a SpooledTemporaryFile or similar
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
