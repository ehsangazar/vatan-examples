"""Run a Gemini batch on Vatan with the google-genai SDK.

Upload the requests, create the batch, wait for it, download the answers.

The only Vatan-specific line in this file is the base URL on the client. Everything
after it is the Gemini SDK unchanged, which is the point: code written against Google
runs against Vatan by changing where it points.

    uv run python run_batch.py
    uv run python run_batch.py --resume batches/7f3a...
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

HERE = Path(__file__).parent
REQUESTS = HERE / "reviews.jsonl"
RESULTS = HERE / "results.jsonl"

# The same model at the batch price. The `:batch` suffix is what chooses it; the plain
# id in a batch is refused rather than quietly run at the live price.
MODEL = os.environ.get("VATAN_BATCH_MODEL", "google/gemini-3.1-flash-lite:batch")

# States a batch will not move on from.
DONE = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED"}


def client() -> genai.Client:
    load_dotenv(HERE / ".env")
    key = os.environ.get("VATAN_API_KEY")
    if not key:
        sys.exit("Set VATAN_API_KEY in .env. Create a key at https://vatan.one/gateway/keys")

    return genai.Client(
        api_key=key,
        http_options={"base_url": os.environ.get("VATAN_BASE_URL", "https://gateway.vatan.one")},
    )


def upload(c: genai.Client) -> str:
    if not REQUESTS.exists():
        sys.exit(f"{REQUESTS.name} is not there. Run: uv run python make_requests.py")

    lines = sum(1 for _ in REQUESTS.open())
    uploaded = c.files.upload(
        file=str(REQUESTS),
        config=types.UploadFileConfig(mime_type="application/jsonl", display_name="reviews"),
    )
    size = int(uploaded.size_bytes or 0)
    print(f"uploaded   {uploaded.name} ({size / 1024:.0f} KB, {lines:,} requests)")
    return uploaded.name


def create(c: genai.Client, file_name: str) -> str:
    job = c.batches.create(
        model=MODEL,
        src=file_name,
        config=types.CreateBatchJobConfig(display_name="review classification"),
    )
    print(f"created    {job.name} on {MODEL}")
    return job.name


def wait(c: genai.Client, name: str) -> types.BatchJob:
    """Poll until the batch stops moving.

    A batch has up to 24 hours, so a real job is told about by a webhook rather than
    watched. See receive_webhook.py. This polls because an example you can run in one
    terminal is easier to follow.
    """
    delay, waited, last = 5, 0.0, None
    while True:
        job = c.batches.get(name=name)
        # `job.state` is an enum, and str() on it gives "JobState.JOB_STATE_SUCCEEDED".
        # Compare on .value, or a finished batch is polled forever.
        state = job.state.value if job.state else ""
        if state != last:
            print(f"waiting    {state}")
            last = state
        if state in DONE:
            print(f"finished   {state} in {waited / 60:.0f}m{waited % 60:.0f}s")
            return job
        time.sleep(delay)
        waited += delay
        # Back off to a minute. Polling a 24-hour job every five seconds is a lot of
        # requests to learn nothing.
        delay = min(delay * 1.5, 60)


def download(c: genai.Client, job: types.BatchJob) -> None:
    if not job.dest or not job.dest.file_name:
        sys.exit(f"The batch ended {job.state} with no results file.")

    raw = c.files.download(file=job.dest.file_name)
    answered = failed = 0

    with RESULTS.open("w") as out:
        for line in raw.decode().splitlines():
            if not line.strip():
                continue
            got = json.loads(line)
            # A failed item comes back as an error line rather than as an empty answer,
            # so count both rather than assuming every line is a result.
            if "error" in got:
                failed += 1
                out.write(json.dumps({"key": got.get("key"), "error": got["error"]["message"]}) + "\n")
                continue
            answered += 1
            text = got["response"]["candidates"][0]["content"]["parts"][0]["text"].strip()
            out.write(json.dumps({"key": got.get("key"), "verdict": text}) + "\n")

    print(f"results    {RESULTS.name}, {answered:,} answers, {failed:,} failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", metavar="BATCH", help="wait on a batch that already exists")
    parser.add_argument("--keep-file", action="store_true", help="do not delete the input file")
    args = parser.parse_args()

    c = client()

    if args.resume:
        download(c, wait(c, args.resume))
        return

    file_name = upload(c)
    name = create(c, file_name)
    job = wait(c, name)
    download(c, job)

    # The input file is yours to clean up; the output file belongs to the batch and
    # stays with it. Files count against your workspace's storage until deleted.
    if not args.keep_file:
        c.files.delete(name=file_name)
        print(f"cleaned    deleted {file_name}")


def run(main_fn) -> None:
    """Run an example and report a refusal the way the gateway wrote it.

    The gateway explains itself in `error.message`: which key, how much
    budget is left, what the request could have cost. A traceback buries
    that under sixty lines of SDK internals, and the one line worth
    reading is the last one.
    """
    try:
        main_fn()
    except errors.APIError as e:
        sys.exit(f"\n{e.code}: {e.message}")
    except KeyboardInterrupt:
        sys.exit("\nstopped")


if __name__ == "__main__":
    run(main)
