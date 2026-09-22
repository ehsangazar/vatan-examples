"""Talking to a model on Vatan: one answer, a stream, and a conversation.

The only Vatan-specific line is the base URL. Everything after it is the Gemini
SDK you already know.

    uv run python chat.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

HERE = Path(__file__).parent
MODEL = os.environ.get("VATAN_MODEL", "google/gemini-3.1-flash-lite")


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

    # ── One answer ────────────────────────────────────────────────────────
    answer = c.models.generate_content(
        model=MODEL,
        contents="Name the three largest moons of Jupiter. Just the names.",
        config=types.GenerateContentConfig(max_output_tokens=60, temperature=0),
    )
    print("answer     :", (answer.text or "").strip().replace("\n", " "))

    # What it cost you, and on which model. Vatan reports usage the same way
    # Google does, so code that reconciles tokens keeps working.
    u = answer.usage_metadata
    print(f"usage      : {u.prompt_token_count} in, {u.candidates_token_count} out, model {answer.model_version}")

    # ── A system instruction ──────────────────────────────────────────────
    terse = c.models.generate_content(
        model=MODEL,
        contents="Why is the sky blue?",
        config=types.GenerateContentConfig(
            system_instruction="Answer in exactly one short sentence. No preamble.",
            max_output_tokens=80,
        ),
    )
    print("system     :", (terse.text or "").strip())

    # ── Streaming ─────────────────────────────────────────────────────────
    # Each chunk arrives as it is generated. Useful when a person is waiting.
    print("streaming  : ", end="", flush=True)
    for chunk in c.models.generate_content_stream(
        model=MODEL,
        contents="Count from one to five in words, comma separated.",
        config=types.GenerateContentConfig(max_output_tokens=60, temperature=0),
    ):
        print(chunk.text or "", end="", flush=True)
    print()

    # ── A conversation that remembers ─────────────────────────────────────
    # `chats` keeps the history for you and sends it with each turn, so the
    # model can refer back. You are charged for the whole history every turn,
    # which is the thing to know before you use it for something long.
    chat = c.chats.create(model=MODEL)
    chat.send_message("My favourite colour is teal. Reply with OK.")
    back = chat.send_message("What is my favourite colour? One word.")
    print("chat recall:", (back.text or "").strip())

    # ── Counting before you send ──────────────────────────────────────────
    # Answered by Google's own counter, so it is the number that will be
    # charged rather than an estimate.
    counted = c.models.count_tokens(model=MODEL, contents="How many tokens is this sentence?")
    print("count      :", counted.total_tokens, "tokens")

    # ── When the answer is cut off ────────────────────────────────────────
    # A short budget stops mid-sentence and says so. Check finish_reason before
    # treating an answer as complete; MAX_TOKENS means there was more to come.
    short = c.models.generate_content(
        model=MODEL,
        contents="Describe the water cycle.",
        config=types.GenerateContentConfig(max_output_tokens=10),
    )
    print("truncated  :", short.candidates[0].finish_reason)


if __name__ == "__main__":
    main()
