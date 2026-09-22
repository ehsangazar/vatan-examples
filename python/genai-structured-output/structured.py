"""Getting JSON back from a model on Vatan, in a shape you decided.

Three ways, in the order you should reach for them: a Pydantic class, a plain
schema, and a bare JSON instruction. The first is worth the import.

    uv run python structured.py
"""

import json
import os
import sys
from enum import Enum
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
from pydantic import BaseModel

HERE = Path(__file__).parent
MODEL = os.environ.get("VATAN_MODEL", "google/gemini-3.1-flash-lite")

REVIEW = (
    "Ordered the stand on Tuesday, it turned up Thursday which is quicker than promised. "
    "Solid aluminium, no wobble at all. The instructions are a single unlabelled diagram "
    "and I put the arm on backwards first go. Would still buy it again."
)


class Sentiment(str, Enum):
    positive = "positive"
    negative = "negative"
    mixed = "mixed"


class Review(BaseModel):
    """What we want out of a review, as a class rather than a prompt.

    The field names and types ARE the instruction: the SDK turns this into a
    schema, and `response.parsed` hands back one of these rather than a string
    you have to trust and parse.
    """

    sentiment: Sentiment
    delivery_days: int
    praised: list[str]
    complained_about: list[str]


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

    # ── A Pydantic class ──────────────────────────────────────────────────
    # The one to use. You get a typed object back, and a field that comes back
    # wrong fails here rather than three functions later.
    answer = c.models.generate_content(
        model=MODEL,
        contents=f"Extract the details from this review:\n\n{REVIEW}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Review,
            max_output_tokens=500,
            temperature=0,
        ),
    )
    review: Review = answer.parsed
    print("parsed as a class:")
    print(f"  sentiment      {review.sentiment.value}")
    print(f"  delivery_days  {review.delivery_days}")
    print(f"  praised        {', '.join(review.praised)}")
    print(f"  complained     {', '.join(review.complained_about)}")

    # ── A plain schema ────────────────────────────────────────────────────
    # When the shape is decided somewhere else, or comes from a config file.
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "score": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["title", "score"],
    }
    plain = c.models.generate_content(
        model=MODEL,
        contents=f"Give this review a one-line title and a score out of five:\n\n{REVIEW}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=schema,
            max_output_tokens=200, temperature=0,
        ),
    )
    print("\nfrom a plain schema:", json.loads(plain.text or "{}"))

    # ── JSON with no schema ───────────────────────────────────────────────
    # Valid JSON, shape up to the model. Use it when the shape really is open;
    # if you know the shape, the two above are strictly better.
    loose = c.models.generate_content(
        model=MODEL,
        contents=f"Summarise this review as JSON, with whatever fields you think fit:\n\n{REVIEW}",
        config=types.GenerateContentConfig(response_mime_type="application/json", max_output_tokens=300),
    )
    print("\nJSON, shape up to the model:", ", ".join(json.loads(loose.text or "{}").keys()))

    # ── A list of them ────────────────────────────────────────────────────
    # The same thing over many inputs. For thousands of these, do it as a batch
    # at half the price: see ../genai-batch.
    many = c.models.generate_content(
        model=MODEL,
        contents="Invent three short product reviews and extract each one.",
        config=types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=list[Review],
            max_output_tokens=900, temperature=0.4,
        ),
    )
    print(f"\na list of them: {len(many.parsed)} reviews, sentiments "
          f"{', '.join(r.sentiment.value for r in many.parsed)}")


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
