"""Minimal HTTP wrapper for Cloud Run.

Exposes POST /ask {"question": ..., "session_id": ...} -> {"answer": ...}
Uses only the stdlib so the container stays small.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import answer


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: dict) -> None:
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # health check for Cloud Run
        if self.path == "/healthz":
            self._send(200, {"status": "ok"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/ask":
            self._send(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        q = data.get("question", "")
        result = answer(q, data.get("session_id"))
        self._send(200, {"answer": result})


def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
