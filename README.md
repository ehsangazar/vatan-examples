# Vatan examples

Working examples of the [Vatan](https://vatan.one) API, each one a small project you can
run rather than a snippet you have to assemble.

Vatan is a model gateway. One key and one base URL reach every model it carries, from
Gemini and Claude to GPT and open-weight models, with per-key budgets, spend caps and a
batch API behind the same credential.

## What is here

| Example | What it shows |
| --- | --- |
| [`python/gemini-batch`](python/gemini-batch) | Classify thousands of texts overnight at the batch price, using Google's own `google-genai` SDK pointed at Vatan. Covers Files, the batch API and a webhook for when the job finishes. |
| [`python/files`](python/files) | Every Files operation on its own: upload, list, retrieve, download, delete. What a batch reads from and writes back to. |

## Before you start

Every example needs a Vatan API key. Create one at
[vatan.one/gateway/keys](https://vatan.one/gateway/keys), then copy `.env.example` to
`.env` in the example's folder and paste the key in.

A key carries its own budget and rate limit, so a key you give to an example script is
a key that cannot spend more than you decided when you made it. Set a small budget on
it and you can run these without watching.

## Licence

MIT. Take any of it.
