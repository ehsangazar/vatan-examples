# Semantic search on Vatan

An embedding turns text into a list of numbers, and two pieces of text that mean
similar things end up near each other. This example embeds five documents and answers
three questions that share almost no words with them.

## Running it

```bash
cp .env.example .env
uv sync
uv run python search.py
```

```
'how long until I get my money back'
  -> Refunds are issued to the original payment method within five working days.
     score 0.722, next best 0.561, gap 0.160
```

None of those words appear in the document. That is the point.

## Worth knowing

**Embed one text per request.** Handing the SDK a list packs them into a single
content with several parts, and that is embedded as ONE thing: you get one vector for
the lot rather than one each. It still runs and still returns numbers, which is what
makes it worth saying out loud.

**The gap between first and second is the signal.** A small gap means your corpus has
no good answer, and saying so beats returning the top row anyway.

**Pick the width when you build the index.** A narrower vector is cheaper to store and
faster to compare. Changing it later means re-embedding everything, because vectors of
different widths cannot be compared at all.

**`taskType` is refused rather than ignored.** Google lets you say whether text is a
document or a query. Vatan has no field to carry it, and accepting it and dropping it
would quietly degrade your recall, so it is refused by name. Embed your documents and
your queries the same way.

**`google/gemini-embedding-2` is the strongest model on Persian that Vatan carries**,
which is a large part of why this example exists.
