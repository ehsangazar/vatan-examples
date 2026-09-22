"""Semantic search on Vatan: embed a few documents, then find the right one.

An embedding turns text into a list of numbers, and two pieces of text that mean
similar things end up near each other. That is the whole trick behind search that
works on meaning rather than on matching words.

    uv run python search.py

`google/gemini-embedding-2` is the strongest model on Persian that Vatan carries,
which is why this example exists as much as the search does.
"""

import math
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

HERE = Path(__file__).parent
MODEL = os.environ.get("VATAN_EMBED_MODEL", "google/gemini-embedding-2")

DOCS = [
    "Refunds are issued to the original payment method within five working days.",
    "Our warehouse is closed on public holidays, so orders placed then ship the next day.",
    "The annual leave allowance is 25 days plus public holidays, rising to 30 after five years.",
    "To reset your password, use the link on the sign-in page; it expires after an hour.",
    "Expenses under £50 need no receipt. Anything above needs one attached to the claim.",
]

QUERIES = [
    "how long until I get my money back",
    "I am locked out of my account",
    "do I need a receipt for a £12 taxi",
]


def client() -> genai.Client:
    load_dotenv(HERE / ".env")
    key = os.environ.get("VATAN_API_KEY")
    if not key:
        sys.exit("Set VATAN_API_KEY in .env. Create a key at https://vatan.one/gateway/keys")
    return genai.Client(
        api_key=key,
        http_options={"base_url": os.environ.get("VATAN_BASE_URL", "https://gateway.vatan.one")},
    )


def cosine(a: list[float], b: list[float]) -> float:
    """How close two embeddings are, from -1 to 1. Higher is more alike."""
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def embed(c: genai.Client, texts: list[str], dimensions: int | None = None) -> list[list[float]]:
    """Embed each text and hand back one vector per text.

    One request per text, deliberately. Handing the SDK a list packs them into a
    single content with several parts, and Google embeds THAT as one thing: you
    get one vector for the lot rather than one each. It is the kind of wrong that
    still runs and still returns numbers.
    """
    config = types.EmbedContentConfig(output_dimensionality=dimensions) if dimensions else None
    return [c.models.embed_content(model=MODEL, contents=t, config=config).embeddings[0].values
            for t in texts]


def main() -> None:
    c = client()

    print(f"embedding {len(DOCS)} documents with {MODEL}")
    library = embed(c, DOCS)
    print(f"each vector is {len(library[0])} numbers long\n")

    for query in QUERIES:
        wanted = embed(c, [query])[0]
        scored = sorted(((cosine(wanted, v), d) for v, d in zip(library, DOCS)), reverse=True)
        best, doc = scored[0]
        runner_up = scored[1][0]
        print(f"{query!r}")
        print(f"  -> {doc}")
        # The gap between first and second is the useful signal. A small gap means
        # the corpus has no good answer and you should say so rather than return
        # the top row anyway.
        print(f"     score {best:.3f}, next best {runner_up:.3f}, gap {best - runner_up:.3f}\n")

    # ── Smaller vectors ───────────────────────────────────────────────────
    # A narrower vector is cheaper to store and faster to compare, and loses some
    # accuracy. Pick the width when you build the index: changing it later means
    # re-embedding everything, because vectors of different widths cannot be
    # compared at all.
    narrow = embed(c, [DOCS[0]], dimensions=256)[0]
    print(f"the same document at 256 dimensions: {len(narrow)} numbers")


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
