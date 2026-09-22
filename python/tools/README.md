# Tool calling on Vatan

You hand the SDK ordinary Python functions. It shows the model what they take, the
model asks for the ones it wants, the SDK runs them and sends the results back, and
the model answers using them. That loop is what an agent is.

## Running it

```bash
cp .env.example .env
uv sync
uv run python tools.py
```

```
one tool:
   [tool] stock_level('widget')
  -> We have 41 widgets in stock.

two calls in one turn:
   [tool] stock_level('widget')
   [tool] stock_level('sprocket')
  -> We have 41 widgets and 7 sprockets in stock, so we have more widgets.

two tools, chained:
   [tool] stock_level('gizmo')
   [tool] restock_cost('gizmo', 20)
  -> We have 0 gizmos in stock. Since this is fewer than five, I have ordered 20.
     The total cost for the order is $70.00.
```

## ⚠ Do not use `from __future__ import annotations` in a file that defines tools

It breaks automatic function calling in the SDK. The callable errors when it is
invoked, so the model calls your tool, gets an error back, tries once more, and gives
up with something like *"the tool is currently experiencing a technical issue."*

It looks like the model failing, or the gateway failing, and it is neither. The import
is extremely common in modern Python and this costs people hours. Keep it out of files
that define tools, or declare those tools by hand instead.

## Worth knowing

**Parallel calling is on by default.** The model can ask for several calls in one turn
rather than taking a round trip each, which is why the second example runs two lookups
before answering.

**Chaining happens when the second call needs the first one's answer.** The third
example asks for a stock level and an order conditional on it, so the model looks it
up before deciding. Hand it the stock level in the prompt and it will skip the lookup,
which is correct behaviour and looks like a broken example.

**The docstring is the instruction.** The SDK builds the tool description and the
argument schema from your function's signature and docstring, so an `Args:` section
that names each parameter is doing real work.

**Declare by hand when the thing is not a local function.** An HTTP service, a queue,
another team's API: declare the shape, read the `function_call` off the response, run
it yourself, and send a `functionResponse` back. The last section shows the shape.

**Tool results are not free.** Every turn resends the conversation so far, including
the results, so a long loop costs more than it looks.
