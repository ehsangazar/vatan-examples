"""Receive `batch.finished` from Vatan, and verify it before trusting it.

Polling is fine for an example. A nightly job wants to be told, so Vatan calls a
webhook when a batch ends.

    uv run python receive_webhook.py          # listens on http://localhost:8787/

Point a webhook at this URL (through a tunnel, or run it somewhere public), paste
its signing secret into .env as VATAN_WEBHOOK_SECRET, and subscribe it to
`batch.finished` at https://vatan.one/admin/webhooks.

To try it without hosting anything, choose Vatan's own test receiver when you
create the webhook. Vatan then holds the deliveries for you and you read them on
the webhook's **Received** tab in the console. There is no API credential that
reads them back: a gateway key cannot call the control plane, and a management
key is scoped to issuing and revoking keys and nothing else. The console is the
only way, and that is deliberate rather than an omission.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv

HERE = Path(__file__).parent
PORT = 8787
# A delivery older than this is refused even when its signature is good, so a
# captured one cannot be replayed at you next week.
MAX_AGE_SECONDS = 300


def verify(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    """The whole of it: HMAC-SHA256 over `timestamp.body`, compared in constant time.

    Do this before trusting anything in the body. An unverified webhook endpoint is
    one anyone on the internet can post to, and `batch.finished` is a message that
    makes programs spend money.
    """
    signed = timestamp.encode() + b"." + body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class Handler(BaseHTTPRequestHandler):
    secret = ""

    def do_POST(self) -> None:  # noqa: N802 - the base class names it
        body = self.rfile.read(int(self.headers.get("content-length") or 0))
        timestamp = self.headers.get("x-vatan-timestamp", "")
        signature = self.headers.get("x-vatan-signature", "")

        if not (self.secret and verify(self.secret, timestamp, body, signature)):
            print("REFUSED  a delivery whose signature did not check out")
            self.send_response(401)
            self.end_headers()
            return

        # Age is checked separately from the signature. A correctly signed delivery
        # from last week is still a replay.
        try:
            age = abs(time.time() - float(timestamp))
        except ValueError:
            age = MAX_AGE_SECONDS + 1
        if age > MAX_AGE_SECONDS:
            print(f"REFUSED  a delivery {age:.0f}s old, which is older than this receiver accepts")
            self.send_response(401)
            self.end_headers()
            return

        # 2xx first, and quickly. Vatan retries anything that times out or fails, so
        # slow work belongs after the response, not before it.
        self.send_response(200)
        self.end_headers()

        envelope = json.loads(body)
        event = envelope.get("event")
        data = envelope.get("data", {})
        print(f"\n{event}  {envelope.get('id')}  attempt {self.headers.get('x-vatan-attempt', '1')}")

        if event == "batch.finished":
            # The counts sit directly on `data`, and the batch is `batch_id`. Read off
            # a real delivery, not inferred from the Batch object, which nests them.
            print(f"  batch   {data.get('batch_id')}")
            print(f"  model   {data.get('model')}")
            print(f"  status  {data.get('api_status') or data.get('status')}")
            print(
                f"  counts  {data.get('total', 0):,} total, "
                f"{data.get('completed', 0):,} completed, {data.get('failed', 0):,} failed"
            )
            print("  -> this is where you would download the results and carry on")

    def log_message(self, *args: object) -> None:
        """Quiet: the handler prints what matters itself."""


def main() -> None:
    load_dotenv(HERE / ".env")
    Handler.secret = os.environ.get("VATAN_WEBHOOK_SECRET", "")
    if not Handler.secret:
        print(
            "VATAN_WEBHOOK_SECRET is not set, so every delivery will be refused.\n"
            "Create the webhook at https://vatan.one/admin/webhooks and copy its signing\n"
            "secret into .env. Running anyway, so you can see the refusal.\n"
        )
    print(f"listening on http://localhost:{PORT}/  (ctrl-c to stop)")
    HTTPServer(("", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
