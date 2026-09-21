"""Read back what Vatan sent to your webhook when the batch finished.

Polling is fine for an example. A nightly job wants to be told, so Vatan calls a webhook
on `batch.finished` and eleven other events.

Set the webhook up once in the console, at https://vatan.one/admin/webhooks:
pick the Vatan test receiver so you do not need a public server, subscribe it to
`batch.finished`, and put its id in .env as VATAN_WEBHOOK_ID.

Reading deliveries back needs a MANAGEMENT key, which is a different credential from
your API key: https://vatan.one/admin/keys. Without one, the same deliveries are on the
webhook's Received tab in the console.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).parent
CONTROL_PLANE = "https://api.vatan.one"


def verify(secret: str, timestamp: str, body: str, signature: str) -> bool:
    """The whole of it: HMAC-SHA256 over `timestamp.body`, compared in constant time.

    Do this on your own receiver before trusting anything in the body. An unverified
    webhook is an endpoint anyone on the internet can post to, and `batch.finished` is a
    message that makes programs spend money.

    The timestamp is there so a captured delivery cannot be replayed at you a week
    later: reject anything more than a few minutes old, as well as anything unsigned.
    """
    expected = hmac.new(secret.encode(), f"{timestamp}.{body}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def main() -> None:
    load_dotenv(HERE / ".env")
    webhook = os.environ.get("VATAN_WEBHOOK_ID")
    management = os.environ.get("VATAN_MANAGEMENT_KEY")

    if not webhook:
        sys.exit(
            "Set VATAN_WEBHOOK_ID in .env.\n"
            "Create the webhook at https://vatan.one/admin/webhooks, choose the Vatan test\n"
            "receiver, and subscribe it to batch.finished."
        )
    if not management:
        sys.exit(
            "Set VATAN_MANAGEMENT_KEY in .env to read deliveries from here.\n"
            "Create one at https://vatan.one/admin/keys. It is a different credential from\n"
            "your API key, on purpose: an API key spends money and cannot read your account.\n"
            "\n"
            "Or skip this script: the same deliveries are on the webhook's Received tab at\n"
            f"https://vatan.one/admin/webhooks/{webhook}"
        )

    answer = httpx.get(
        f"{CONTROL_PLANE}/v1/webhooks/{webhook}/received",
        headers={"authorization": f"Bearer {management}"},
        timeout=30,
    )
    if answer.status_code == 401:
        sys.exit("That management key was refused. Check it is a management key and not an API key.")
    answer.raise_for_status()

    received = answer.json().get("data", [])
    if not received:
        sys.exit("Nothing has arrived yet. Run a batch, or send a test from the console.")

    for got in received:
        if got.get("event") != "batch.finished":
            continue

        age = int(got.get("age_seconds") or 0)
        when = f"{age // 60} minutes ago" if age >= 60 else f"{age} seconds ago"
        # The test receiver verifies the signature for you and reports it. On your own
        # receiver, do it yourself with verify() above.
        seal = "signature verified" if got.get("verified") else "NOT VERIFIED"
        print(f"{got['event']}   {got.get('event_id')}   {when}   {seal}")

        body = got.get("body")
        data = (json.loads(body) if isinstance(body, str) else body or {}).get("data", {})
        counts = data.get("request_counts", {})
        print(f"  batch     {data.get('id')}")
        print(f"  status    {data.get('status')}")
        print(
            f"  counts    {counts.get('total', 0):,} total, "
            f"{counts.get('completed', 0):,} completed, {counts.get('failed', 0):,} failed"
        )
        return

    print("Deliveries arrived, but none of them were batch.finished.")
    print("Check the webhook is subscribed to that event.")


if __name__ == "__main__":
    main()
