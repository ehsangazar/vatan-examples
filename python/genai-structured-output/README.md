# JSON back, in a shape you decided

Three ways, in the order you should reach for them: a Pydantic class, a plain schema,
and a bare JSON instruction.

## Running it

```bash
cp .env.example .env
uv sync
uv run python structured.py
```

```
parsed as a class:
  sentiment      positive
  delivery_days  2
  praised        fast delivery, solid aluminium, no wobble
  complained     unlabelled assembly instructions

from a plain schema: {'title': 'Sturdy stand with minor assembly frustration', 'score': 4}
```

## Worth knowing

**Use the Pydantic class.** `response.parsed` hands back a typed object instead of a
string you have to trust and parse, and a field that comes back wrong fails there
rather than three functions later.

**A schema is an instruction, not a filter.** It shapes what the model produces; it
does not sanitise it afterwards. Validate anything you are about to act on.

**An enum narrows the answer usefully.** `Sentiment` in this example stops the model
inventing a fourth category, which is the common failure when you ask for a label in
prose.

**For thousands of these, run them as a batch** at roughly half the price. See
[`../genai-batch`](../genai-batch).
