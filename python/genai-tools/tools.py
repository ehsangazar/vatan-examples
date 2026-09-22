"""Tool calling on Vatan: let the model run your Python functions.

You hand the SDK ordinary functions. It shows the model what they take, the model
asks for the ones it wants, the SDK runs them and sends the results back, and the
model answers using them. That loop is what an agent is.

    uv run python tools.py

⚠ Do NOT put `from __future__ import annotations` at the top of a file that
defines tools. It breaks automatic function calling in the SDK: the callable
errors when it is invoked, the model gets an error back, tries once more, and
gives up with "the tool is currently experiencing a technical issue". It looks
like the model or the gateway failing and it is neither. See the README.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

HERE = Path(__file__).parent
MODEL = os.environ.get("VATAN_MODEL", "google/gemini-3.1-flash-lite")

# A stand-in for whatever you actually have: a database, an internal API, a
# calculation nobody wants the model guessing at.
STOCK = {"widget": 41, "gizmo": 0, "sprocket": 7}


def lookup(product: str) -> int | None:
    """Find a product however the model spelled it.

    The model will hand you "widgets" when your keys say "widget". Take the
    plural off before you decide something does not exist: a tool that answers
    "we do not carry that" to a real product is worse than no tool, because the
    model believes it and tells the customer.
    """
    name = product.strip().lower()
    return STOCK.get(name) or STOCK.get(name.rstrip("s"))


def stock_level(product: str) -> str:
    """How many of a product are in the warehouse.

    Args:
        product: the product name, for example "widget"
    """
    print(f"   [tool] stock_level({product!r})")
    n = lookup(product)
    return f"{product}: not a product we carry" if n is None else f"{product}: {n} in stock"


def restock_cost(product: str, quantity: int) -> str:
    """What it costs to order more of a product.

    Args:
        product: the product name
        quantity: how many to order
    """
    print(f"   [tool] restock_cost({product!r}, {quantity})")
    return f"{quantity} x {product} costs ${quantity * 3.50:.2f}"


def client() -> genai.Client:
    load_dotenv(HERE / ".env")
    key = os.environ.get("VATAN_API_KEY")
    if not key:
        sys.exit("Set VATAN_API_KEY in .env. Create a key at https://vatan.one/gateway/keys")
    return genai.Client(
        api_key=key,
        http_options={"base_url": os.environ.get("VATAN_BASE_URL", "https://gateway.vatan.one")},
    )


def main() -> None:
    c = client()

    # ── One tool, one call ────────────────────────────────────────────────
    print("one tool:")
    answer = c.models.generate_content(
        model=MODEL,
        contents="How many widgets do we have?",
        config=types.GenerateContentConfig(tools=[stock_level], max_output_tokens=300),
    )
    print("  ->", (answer.text or "").strip())

    # ── Two calls in one turn ─────────────────────────────────────────────
    # The model asks for both at once rather than taking two round trips.
    # Parallel calling is on by default on Gemini.
    print("\ntwo calls in one turn:")
    both = c.models.generate_content(
        model=MODEL,
        contents="Do we have more widgets or more sprockets? Check both.",
        config=types.GenerateContentConfig(tools=[stock_level], max_output_tokens=400),
    )
    print("  ->", (both.text or "").strip())

    # ── Two different tools, chained ──────────────────────────────────────
    # The second call depends on what the first one returns, so the model has to
    # look the stock up before it can decide whether to order anything. Give it
    # the answer in the prompt instead and it will skip the lookup, correctly.
    print("\ntwo tools, chained:")
    chained = c.models.generate_content(
        model=MODEL,
        contents="How many gizmos do we have? If it is fewer than five, order 20 "
                 "and tell me what that costs.",
        config=types.GenerateContentConfig(tools=[stock_level, restock_cost], max_output_tokens=500),
    )
    print("  ->", (chained.text or "").strip())

    # ── Declaring a tool by hand ──────────────────────────────────────────
    # When the thing the model calls is not a local Python function -- an HTTP
    # service, a queue, another team's API -- declare the shape and handle the
    # call yourself. Nothing runs automatically here.
    print("\ndeclared by hand, no automatic execution:")
    declared = types.Tool(function_declarations=[types.FunctionDeclaration(
        name="open_ticket",
        description="Open a support ticket",
        parameters={
            "type": "object",
            "properties": {"summary": {"type": "string"}, "urgent": {"type": "boolean"}},
            "required": ["summary"],
        },
    )])
    asked = c.models.generate_content(
        model=MODEL,
        contents="The gizmo line is down and it is urgent. Open a ticket.",
        config=types.GenerateContentConfig(tools=[declared], max_output_tokens=300),
    )
    for part in asked.candidates[0].content.parts or []:
        if part.function_call:
            print(f"  -> the model asked for {part.function_call.name}({dict(part.function_call.args)})")
            print("     you would run it and send the result back as a functionResponse")


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
