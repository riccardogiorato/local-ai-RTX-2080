#!/usr/bin/env python3
# stdlib-only rewrite of upstream service/upstream/decryptor_server.py.orig
# (flask->http.server, no deps); identical API contract: POST /decrypt with
# {"incantation": ...}; on success writes results.txt under TASK_ROOT.
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SECRET_INCANTATION = "ECHOES-OF-CYPRESS"
FINAL_MESSAGE = "What is etched, endures."
ROOT = Path(os.environ.get("TASK_ROOT", "."))

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/decrypt":
            self.send_error(404); return
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            data = json.loads(body or b"{}")
        except Exception:
            data = {}
        inc = (data or {}).get("incantation")
        if not inc:
            self._json({"status": "error", "message": "Missing 'incantation' field"}, 400); return
        if inc == SECRET_INCANTATION:
            (ROOT / "results.txt").write_text(FINAL_MESSAGE + "\n")
            self._json({"status": "success", "message": "The ancient secret has been revealed.", "final_message": FINAL_MESSAGE}, 200)
        else:
            self._json({"status": "error", "message": "Wrong incantation. The temple remains silent."}, 403)
    def _json(self, obj, code):
        payload = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    def log_message(self, *a): pass

if __name__ == "__main__":
    port = int(os.environ.get("DECRYPTOR_PORT", "8912"))
    HTTPServer(("127.0.0.1", port), H).serve_forever()
