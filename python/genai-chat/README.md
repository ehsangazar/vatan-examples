# Talking to a model on Vatan

One answer, a system instruction, a stream, a conversation that remembers, a token
count, and what a truncated answer looks like. Start here if you have not used the
gateway before.

```python
client = genai.Client(
    api_key=os.environ["VATAN_API_KEY"],
    http_options={"base_url": "https://gateway.vatan.one"},
)
```

That is the only Vatan-specific line in the file.

## Running it

```bash
cp .env.example .env          # then paste your key into it
uv sync                       # or: pip install -r requirements.txt
uv run python chat.py
```

```
answer     : Ganymede, Callisto, Io
usage      : 13 in, 8 out, model google/gemini-3.1-flash-lite
system     : The sky appears blue because molecules scatter shorter wavelengths more strongly.
streaming  : one, two, three, four, five
chat recall: Teal.
count      : 8 tokens
truncated  : FinishReason.MAX_TOKENS
```

## Worth knowing

**`count_tokens` is Google's own counter**, not an estimate, so it is the number you
will be charged for. It is free.

**A conversation is charged for its whole history, every turn.** `chats` resends
everything so the model can refer back, which is what makes it feel like a
conversation and what makes a long one expensive.

**Check `finish_reason` before trusting an answer is complete.** `MAX_TOKENS` means
the model was still talking when the budget ran out.

**The model id names its vendor**, so `google/gemini-3.1-flash-lite` and
`openrouter/google/gemini-3.1-flash-lite` are the same weights bought two ways.
`GET /v1/models` lists what your workspace can call, with prices.
