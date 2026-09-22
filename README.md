# Vatan examples

Working examples of the [Vatan](https://vatan.one) API, each one a small project you can
run rather than a snippet you have to assemble.

Vatan is a model gateway. One key and one base URL reach every model it carries, from
Gemini and Claude to GPT and open-weight models, with per-key budgets, spend caps and a
batch API behind the same credential.

## What is here

| Example | What it shows |
| --- | --- |
| [`python/genai-chat`](python/genai-chat) | Start here. One answer, a system instruction, streaming, a conversation that remembers, counting tokens before you send, and what a truncated answer looks like. |
| [`python/genai-tools`](python/genai-tools) | Let the model call your own Python functions: one tool, two calls in one turn, two tools chained, and declaring a tool by hand. Includes the `from __future__` import that silently breaks all of it. |
| [`python/genai-structured-output`](python/genai-structured-output) | JSON back in a shape you decided, three ways: a Pydantic class, a plain schema, and a bare JSON instruction. |
| [`python/genai-embeddings`](python/genai-embeddings) | Search that works on meaning rather than matching words, with the gap between first and second place as your confidence signal. |
| [`python/genai-media`](python/genai-media) | Reading an image, drawing one, and making a video, including how to poll a long job without losing work you have paid for. |
| [`python/genai-batch`](python/genai-batch) | Classify thousands of texts overnight at the batch price. Covers Files, the batch API and a webhook for when the job finishes. |
| [`python/genai-batch-file`](python/genai-batch-file) | Every Files operation on its own: upload, list, retrieve, download, delete. What a batch reads from and writes back to. |

Every one of them uses Google's own `google-genai` SDK unchanged. The only
Vatan-specific line in any of these files is the base URL:

```python
client = genai.Client(
    api_key=os.environ["VATAN_API_KEY"],
    http_options={"base_url": "https://gateway.vatan.one"},
)
```

Point that at Vatan and the same code reaches every model Vatan carries, not only
Google's, with one key and one bill.

## Before you start

Every example needs a Vatan API key. Create one at
[vatan.one/gateway/keys](https://vatan.one/gateway/keys), then copy `.env.example` to
`.env` in the example's folder and paste the key in.

A key carries its own budget and rate limit, so a key you give to an example script is
a key that cannot spend more than you decided when you made it. Set a small budget on
it and you can run these without watching.

If a request could take the key past that budget, it is refused before it is sent and
nothing is charged. Every example prints that refusal as a single line saying how much
is left and what the request would have cost.

## Licence

MIT. Take any of it.
