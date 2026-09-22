# Batch files on Vatan, with the google-genai SDK

Upload, list, retrieve, download and delete, in one script you can read top to
bottom.

Files exist on Vatan to feed batches. A batch of ten thousand requests does not
fit in a request body, so it arrives as a file, and the answers come back as
files too. If you only ever run batches you will still touch Files on both ends,
which is why it is worth knowing on its own.

As everywhere else, the only Vatan-specific line is the base URL:

```python
client = genai.Client(
    api_key=os.environ["VATAN_API_KEY"],
    http_options={"base_url": "https://gateway.vatan.one"},
)
```

## Running it

```bash
cp .env.example .env          # then paste your key into it
uv sync                       # or: pip install -r requirements.txt
uv run python manage_files.py
```

```
wrote      sample-requests.jsonl, 645 bytes
uploaded   files/file-3b9e...  645 bytes  state FileState.ACTIVE
retrieved  files/file-3b9e...  created 2026-09-22 07:41:02+00:00
listed     3 file(s) in this workspace
downloaded 645 bytes, first line: {"key": "item-1", "request": {"contents": [...
deleted    files/file-3b9e...
gone       True
```

## What is worth knowing

**Uploads are chunked at 8 MB.** The SDK splits a large file and sends it in
several requests, so a 100 MB upload is thirteen of them. Nothing is held whole
in memory at either end. You do not have to do anything about this, but it
explains what you see on the network.

**A file is validated when you upload it, not when the batch runs.** A line that
cannot be parsed, or a request Vatan cannot run, is refused at upload with the
line number on it. That is the last moment you can fix it for free.

**The limits.** Up to 100 MB per file and 10,000 requests per batch file. Both
are refused before anything is stored.

**Input files are yours, output files belong to the batch.** Delete your input
when you are done with it. A batch's output and error files stay with the batch,
so cleaning up an input never costs you the answers.

**The error file is empty when nothing failed.** It is always created, so do not
read its existence as a sign that something went wrong.

## Where files come from, other than you

A finished batch publishes two of them, an output file and an error file, and
both are downloaded with the same `client.files.download()` this script uses. See
[`../gemini-batch`](../gemini-batch) for the whole loop.
