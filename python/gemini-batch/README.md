# Gemini batch on Vatan, with the google-genai SDK

Classify three thousand product reviews with Gemini, at roughly half the live price,
without holding a connection open while it happens.

The point of this example is that it is **ordinary `google-genai` code**. The only thing
that makes it talk to Vatan is the base URL:

```python
from google import genai

client = genai.Client(
    api_key=os.environ["VATAN_API_KEY"],
    http_options={"base_url": "https://gateway.vatan.one"},
)
```

Everything after that line is the Gemini SDK you already know: `files.upload`,
`batches.create`, `batches.get`, `files.download`. Vatan speaks Google's own API, so
existing Gemini code moves across by changing two lines and nothing else.

## Why use Vatan for this instead of Google directly

You do not have to. What you get by going through Vatan is the things a shared Google
key does not give you: a per-key budget that stops a runaway script, one bill across
every model you use, spend visible per key and per team, and the same code path for
Gemini, Claude, GPT and open-weight models when you want to compare them.

The price is what the model costs Vatan plus 5%.

## Running it

You need Python 3.10 or newer and a Vatan API key from
[vatan.one/gateway/keys](https://vatan.one/gateway/keys).

```bash
cp .env.example .env          # then paste your key into it
uv sync                       # or: pip install -r requirements.txt
uv run python make_requests.py   # writes reviews.jsonl, 3,000 requests
uv run python run_batch.py       # uploads, runs the batch, waits, writes results.jsonl
```

`run_batch.py` prints each stage as it happens:

```
uploaded   files/file-8c21... (412 KB, 3000 requests)
created    batches/7f3a... on google/gemini-3.1-flash-lite:batch
waiting    BATCH_STATE_RUNNING (1200/3000 done)
finished   BATCH_STATE_SUCCEEDED in 6m12s
results    results.jsonl, 3000 answers, 12 failed
```

A batch can take up to 24 hours. This one usually finishes in minutes, but the script is
written so you can stop it and run `uv run python run_batch.py --resume batches/7f3a...`
later, because a real job is not one you sit and watch.

## Being told when it finishes, instead of polling

Polling is fine for three thousand reviews. It is the wrong shape for a nightly job, so
Vatan will call a webhook when a batch ends.

Set one up once, in the console:

1. Go to [vatan.one/admin/webhooks](https://vatan.one/admin/webhooks) and click **New webhook**.
2. Choose **Vatan test receiver**. Vatan hosts the endpoint, so you do not need a public
   server to try this.
3. Subscribe it to **batch.finished**.
4. Copy the webhook id into your `.env` as `VATAN_WEBHOOK_ID`.

Then `check_webhook.py` shows you what arrived:

```bash
uv run python check_webhook.py
```

```
batch.finished   evt_9a1c...   2 minutes ago   signature verified
  batch     7f3a...
  status    completed
  counts    3000 total, 2988 completed, 12 failed
```

Reading the deliveries back needs a **management key**, which is a different credential
from your API key and is created at
[vatan.one/admin/keys](https://vatan.one/admin/keys). Put it in `.env` as
`VATAN_MANAGEMENT_KEY`. If you would rather not make one, the same deliveries are on the
webhook's **Received** tab in the console, and this script will tell you that instead of
failing.

When you point a webhook at your own server rather than the test receiver, verify the
signature before trusting the body. Vatan signs with HMAC-SHA256 over
`timestamp.body` and sends it as `x-vatan-signature`, with the timestamp in
`x-vatan-timestamp`. `check_webhook.py` has the eight lines that do it.

## What else the same client does

Batches are what this example is about, but the base URL change is not
batch-specific. The same client reaches the rest of the Gemini API against
Vatan:

```python
client.models.generate_content(model="google/gemini-3.1-flash-lite", contents="...")
client.models.generate_content_stream(...)        # streaming
client.models.count_tokens(...)                   # Google's own counter, not an estimate
client.models.embed_content(model="google/gemini-embedding-2", contents=[...])
client.models.generate_videos(model="openrouter/bytedance/seedance-2.0", prompt="...")
client.chats.create(model="...").send_message("...")
client.files.upload(...) / get / list / delete / download
```

Tool calling, structured output through `response_schema`, system instructions
and image input all come through as well.

A few things Google's SDK can ask for are not served here, and each one says so
with a sentence rather than a bare 404: `caches` (context caching), `tunings`
(fine-tuning), `auth_tokens` and `file_search_stores`. The Live API needs a
realtime connection Vatan does not serve.

Anything Vatan cannot honour faithfully is refused by name rather than dropped.
`safetySettings` is the one most people hit: it changes what the model returns,
Vatan has no way to pass it through, and silently ignoring it would leave you
believing a filter had been changed when it had not.

## What the files are

| File | What it does |
| --- | --- |
| `make_requests.py` | Writes `reviews.jsonl`, one Gemini request per line, in the shape the batch API takes. |
| `run_batch.py` | Uploads the file, creates the batch, waits for it, downloads the answers. |
| `check_webhook.py` | Reads back what Vatan sent to your webhook, and verifies the signature. |

## Things worth knowing before you run a real job

**Every request needs `maxOutputTokens`.** A batch is checked against your balance before
it is sent, and the worst case cannot be worked out without a bound on the output. A
request without one is refused when you create the batch, naming the line it is on.

**The model id ends in `:batch`.** `google/gemini-3.1-flash-lite:batch` is the same model
as `google/gemini-3.1-flash-lite` at the batch price. Using the plain id in a batch is
refused rather than quietly charged at the live price.

**A batch cannot be stopped once it has reached the provider.** Cancel works up to that
point. After it, the job finishes and is charged, so the useful safety net is a budget on
the key rather than a cancel button.

**Results come back keyed, not ordered.** Each line carries the `key` you put on the
request. Match on that rather than on position.

**Files are yours to clean up.** `DELETE` the input file when you are done with it. The
output file belongs to the batch and stays with it.
