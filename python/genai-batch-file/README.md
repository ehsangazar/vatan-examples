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

**The limits.** Up to 1,400 MB and 100,000 requests per file, both refused
before anything is stored. A Google batch can use the whole file; a batch for
any other provider holds at most 25 MB of requests.

**Input files are yours, output files belong to the batch.** Delete your input
when you are done with it. A batch's output and error files stay with the batch,
so cleaning up an input never costs you the answers.

**The error file is empty when nothing failed.** It is always created, so do not
read its existence as a sign that something went wrong.

## Cleaning up: every page, then delete

`clean_up.py` walks every file in the workspace a page at a time and deletes the
ones whose name starts with a prefix. Without `--delete` it only lists.

```bash
uv run python clean_up.py                                  # list only
uv run python clean_up.py --prefix nightly- --delete       # remove them
```

```
listed     23 file(s), 3 match prefix 'nightly-'
             files/file-4b18...  nightly-2026-09-25.jsonl  358 bytes  2026-09-25
             ...
deleted    files/file-4b18...
```

The two calls it is built on:

```python
files_page = client.files.list(config=types.ListFilesConfig(page_size=100))
for f in files_page:          # follows nextPageToken, so this is every page
    client.files.delete(name=f.name)
```

**`page_size` goes up to 100.** Ask for more and you get 100; leave it out and
you get 50. Iterating the pager follows `nextPageToken` for you, so you see every
file, not only the first page.

**The display name is the one you chose.** Set `display_name` in
`UploadFileConfig` and that is the file's name, as it is on Google. Leave it out
and the file is named after the file on disk. Name your batch inputs with a
prefix and `--prefix` finds them.

**You choose how long a file is kept.** A file is kept 30 days unless you say
otherwise. `UploadFileConfig` has no field for it, so Vatan reads a header,
`x-vatan-expires-after`, in seconds from 3600 (an hour) to 2592000 (30 days).
Put it on the client: the SDK replaces any headers you set on
`UploadFileConfig.http_options` with its own upload headers, so they never
arrive.

```python
short = genai.Client(
    api_key=os.environ["VATAN_API_KEY"],
    http_options={
        "base_url": "https://gateway.vatan.one",
        "headers": {"x-vatan-expires-after": "3600"},   # kept one hour
    },
)
short.files.upload(
    file="nightly-2026-09-27.jsonl",
    config=types.UploadFileConfig(display_name="nightly-2026-09-27", mime_type="application/jsonl"),
)
```

Every other call ignores the header, so a client that carries it changes only
its uploads.

**List first, delete after.** The script collects every page before deleting
anything. Deleting while you walk the pages happens to work on Vatan, but it
skips files on APIs that page by offset.

## Where files come from, other than you

A finished batch publishes two of them, an output file and an error file, and
both are downloaded with the same `client.files.download()` this script uses. See
[`../genai-batch`](../genai-batch) for the whole loop.
