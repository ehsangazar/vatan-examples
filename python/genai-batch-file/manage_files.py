"""Every Files operation on Vatan, through Google's genai SDK.

Upload, list, retrieve, download, delete. Files exist on Vatan to feed batches:
a batch of ten thousand requests does not fit in a request body, so it arrives as
a file and the answers come back as files too.

    uv run python manage_files.py

The only Vatan-specific line is the base URL on the client.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

HERE = Path(__file__).parent
SAMPLE = HERE / "sample-requests.jsonl"


def client() -> genai.Client:
    load_dotenv(HERE / ".env")
    key = os.environ.get("VATAN_API_KEY")
    if not key:
        sys.exit("Set VATAN_API_KEY in .env. Create a key at https://vatan.one/gateway/keys")
    return genai.Client(
        api_key=key,
        http_options={"base_url": os.environ.get("VATAN_BASE_URL", "https://gateway.vatan.one")},
    )


def write_sample(lines: int = 5) -> int:
    """A batch input file: one request per line, each with your own key.

    `maxOutputTokens` is on every request because a batch is checked against your
    balance before it is sent, and the worst case cannot be worked out without a
    bound on the output.
    """
    with SAMPLE.open("w") as f:
        for i in range(1, lines + 1):
            f.write(
                json.dumps(
                    {
                        "key": f"item-{i}",
                        "request": {
                            "contents": [{"role": "user", "parts": [{"text": f"Reply with the number {i} only."}]}],
                            "generationConfig": {"maxOutputTokens": 8, "temperature": 0},
                        },
                    }
                )
                + "\n"
            )
    return SAMPLE.stat().st_size


def main() -> None:
    c = client()
    size = write_sample()
    print(f"wrote      {SAMPLE.name}, {size} bytes")

    # ── Upload ────────────────────────────────────────────────────────────
    # Sent in 8 MB chunks by the SDK, so a 100 MB file is thirteen requests and
    # none of it is held in memory at either end. You do not have to do anything
    # about that; it is worth knowing when you watch the network.
    uploaded = c.files.upload(
        file=str(SAMPLE),
        config=types.UploadFileConfig(mime_type="application/jsonl", display_name="sample requests"),
    )
    print(f"uploaded   {uploaded.name}  {uploaded.size_bytes} bytes  state {uploaded.state}")

    # ── Retrieve ──────────────────────────────────────────────────────────
    got = c.files.get(name=uploaded.name)
    print(f"retrieved  {got.name}  created {got.create_time}")

    # ── List ──────────────────────────────────────────────────────────────
    # Your workspace's files, newest first. Files count against a storage quota,
    # so this is the screen that answers "what is filling it up".
    listed = list(c.files.list())
    print(f"listed     {len(listed)} file(s) in this workspace")
    for f in listed[:5]:
        print(f"             {f.name}  {f.size_bytes or 0} bytes")

    # ── Download ──────────────────────────────────────────────────────────
    # The same call fetches a batch's OUTPUT file, which is the usual reason to
    # download anything. Vatan hands back Gemini-shaped result lines.
    #
    # Pass the NAME and not the File object. The SDK refuses a File whose
    # download_uri is unset with "Only generated files can be downloaded", which
    # is a client-side check that never reaches Vatan; the name goes straight
    # through and the bytes come back.
    raw = c.files.download(file=uploaded.name)
    first = raw.decode().splitlines()[0]
    print(f"downloaded {len(raw)} bytes, first line: {first[:70]}...")

    # ── Delete ────────────────────────────────────────────────────────────
    # An input file is yours to clean up. A batch's output file belongs to the
    # batch and stays with it, so deleting the input never costs you the answers.
    c.files.delete(name=uploaded.name)
    print(f"deleted    {uploaded.name}")

    remaining = [f.name for f in c.files.list()]
    print(f"gone       {uploaded.name not in remaining}")

    SAMPLE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
