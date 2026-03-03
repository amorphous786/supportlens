#!/usr/bin/env python3
"""
Minimal mock Ollama server for CI / E2E testing.

Implements the subset of the Ollama HTTP API consumed by llm_client.py:
  HEAD /              → 200  (liveness probe used by compose healthcheck)
  GET  /              → 200
  GET  /api/tags      → model list containing the configured model
  POST /api/chat      → deterministic chat or classification response
                        supports both stream=true and stream=false

Designed to run with no external dependencies (Python stdlib only).
"""
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEL = "llama3"
PORT = 11434

_TAGS = {
    "models": [
        {
            "name": MODEL,
            "modified_at": "2024-01-01T00:00:00.000Z",
            "size": 1_000_000,
            "digest": "mockdigest",
            "details": {"format": "gguf", "family": "llama"},
        }
    ]
}

# Categories the classifier may return
_VALID_CATS = [
    "Billing",
    "Refund",
    "Account Access",
    "Cancellation",
    "General Inquiry",
]

# Marker strings that appear in the classification prompt but not in chat prompts
_CLASSIFY_MARKERS = {"CATEGORIES", "TASK", "CATEGORY:"}


def _is_classification(messages: list[dict]) -> bool:
    combined = " ".join(m.get("content", "") for m in messages)
    return any(marker in combined for marker in _CLASSIFY_MARKERS)


def _pick_category(messages: list[dict]) -> str:
    text = " ".join(m.get("content", "") for m in messages).lower()
    if "refund" in text:
        return "Refund"
    if "cancel" in text:
        return "Cancellation"
    if "login" in text or "password" in text or "mfa" in text:
        return "Account Access"
    if "bill" in text or "invoice" in text or "charge" in text or "payment" in text:
        return "Billing"
    return "General Inquiry"


def _chat_reply(messages: list[dict]) -> str:
    return (
        "Thank you for reaching out to support. "
        "I can help you with billing questions, refunds, and account access. "
        "Please share more details and I will assist you right away."
    )


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):  # silence access logs
        pass

    # ── helpers ───────────────────────────────────────────────────────────────

    def _send_json(self, code: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    # ── routing ───────────────────────────────────────────────────────────────

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", ""):
            self.send_response(200)
            self.end_headers()
        elif self.path == "/api/tags":
            self._send_json(200, _TAGS)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return

        body = self._read_json()
        messages: list[dict] = body.get("messages", [])
        stream: bool = body.get("stream", False)

        content = (
            _pick_category(messages)
            if _is_classification(messages)
            else _chat_reply(messages)
        )

        now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.end_headers()
            for word in content.split():
                chunk = {
                    "model": MODEL,
                    "created_at": now,
                    "message": {"role": "assistant", "content": word + " "},
                    "done": False,
                }
                self.wfile.write((json.dumps(chunk) + "\n").encode())
                self.wfile.flush()
            done_chunk = {
                "model": MODEL,
                "created_at": now,
                "message": {"role": "assistant", "content": ""},
                "done": True,
                "done_reason": "stop",
                "total_duration": 100_000_000,
                "eval_count": len(content.split()),
            }
            self.wfile.write((json.dumps(done_chunk) + "\n").encode())
            self.wfile.flush()
        else:
            self._send_json(
                200,
                {
                    "model": MODEL,
                    "created_at": now,
                    "message": {"role": "assistant", "content": content},
                    "done": True,
                    "done_reason": "stop",
                    "total_duration": 100_000_000,
                    "eval_count": len(content.split()),
                },
            )


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), _Handler)
    print(f"Mock Ollama listening on 0.0.0.0:{PORT}", flush=True)
    server.serve_forever()
