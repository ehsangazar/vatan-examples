"""Pictures and video on Vatan: reading an image, drawing one, making a video.

    uv run python media.py              # reads an image and draws one
    uv run python media.py --video      # also makes a video, which costs real money

Three different models do these three jobs, so each section names its own. What
they have in common is the base URL.
"""

import argparse
import base64
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

HERE = Path(__file__).parent

# Reads pictures and answers in text.
VISION_MODEL = os.environ.get("VATAN_VISION_MODEL", "google/gemini-3.1-flash-lite")
# Draws pictures. It answers at the chat endpoint and returns the image beside
# the text, which is why it is a chat model here rather than an image endpoint.
IMAGE_MODEL = os.environ.get("VATAN_IMAGE_MODEL", "openrouter/google/gemini-2.5-flash-image")
# Makes video. Priced per second AT EACH RESOLUTION, so a resolution is required.
VIDEO_MODEL = os.environ.get("VATAN_VIDEO_MODEL", "openrouter/google/veo-3.1-lite")

# A 16x16 red square, so the example needs no files beside it.
RED_SQUARE = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAIAAACQkWg2AAAAJ0lEQVR4nGP8z4AATAxUZ4"
    "xqGNUwqmFUw6iGUQ2jGkY1jGoY1QAAmO4CAU9wJ1kAAAAASUVORK5CYII="
)


def client() -> genai.Client:
    load_dotenv(HERE / ".env")
    key = os.environ.get("VATAN_API_KEY")
    if not key:
        sys.exit("Set VATAN_API_KEY in .env. Create a key at https://vatan.one/gateway/keys")
    return genai.Client(
        api_key=key,
        http_options={"base_url": os.environ.get("VATAN_BASE_URL", "https://gateway.vatan.one")},
    )


def read_a_picture(c: genai.Client) -> None:
    """Send an image with your question and get an answer about it."""
    print("reading a picture")
    answer = c.models.generate_content(
        model=VISION_MODEL,
        contents=[
            types.Part.from_bytes(data=RED_SQUARE, mime_type="image/png"),
            "What colour is this square? One word.",
        ],
        config=types.GenerateContentConfig(max_output_tokens=20),
    )
    print("  ->", (answer.text or "").strip())


def draw_a_picture(c: genai.Client) -> None:
    """Ask for an image back.

    `response_modalities` is how you say you want a picture. The image arrives as
    an inline_data part beside any text, so walk the parts rather than reading
    `.text` and wondering where the picture went.
    """
    print("\ndrawing a picture")
    answer = c.models.generate_content(
        model=IMAGE_MODEL,
        contents="A single yellow rubber duck on a plain white background, product photo.",
        config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"], max_output_tokens=2048),
    )
    for part in answer.candidates[0].content.parts or []:
        if part.text:
            print("  text:", part.text.strip()[:70])
        if part.inline_data:
            out = HERE / "duck.png"
            out.write_bytes(part.inline_data.data)
            print(f"  image: {out.name}, {len(part.inline_data.data):,} bytes, {part.inline_data.mime_type}")


def make_a_video(c: genai.Client) -> None:
    """Start a video, wait for it, download it.

    A video is a long-running operation rather than a reply: you get an operation
    back, poll it, and fetch the bytes when it is done. Minutes, not seconds.

    A resolution is REQUIRED because a video is priced per second at each
    resolution, and Vatan will not start a job it cannot price. GET /v1/models
    lists the resolutions a model is priced at.
    """
    print("\nmaking a video (this costs real money and takes a minute)")
    started = time.time()
    op = c.models.generate_videos(
        model=VIDEO_MODEL,
        prompt="A paper boat floating down a rain gutter, close up, grey daylight.",
        config=types.GenerateVideosConfig(duration_seconds=4, aspect_ratio="16:9", resolution="720p"),
    )
    print(f"  operation {op.name}")

    # A poll that fails is not a job that failed. Rendering takes minutes and
    # anything on a network for minutes will occasionally answer 502; the job
    # carries on regardless. Seen once in testing, at 53 seconds, on a job that
    # finished normally afterwards. Give up only after several in a row.
    stumbles = 0
    while not op.done:
        time.sleep(10)
        try:
            op = c.operations.get(op)
            stumbles = 0
        except Exception as e:  # noqa: BLE001 - any transport failure is the same here
            stumbles += 1
            print(f"  poll failed ({type(e).__name__}), retrying {stumbles}/3")
            if stumbles >= 3:
                print("  giving up on the poll; the job may still finish. Its name is above.")
                return
            continue
        print(f"  waiting ({time.time() - started:.0f}s)")

    if op.error:
        print("  failed:", str(op.error)[:160])
        return

    video = op.response.generated_videos[0].video
    out = HERE / "boat.mp4"
    out.write_bytes(c.files.download(file=video))
    print(f"  video: {out.name}, {out.stat().st_size:,} bytes in {time.time() - started:.0f}s")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", action="store_true", help="also make a video, which costs real money")
    args = parser.parse_args()

    c = client()
    read_a_picture(c)
    draw_a_picture(c)
    if args.video:
        make_a_video(c)
    else:
        print("\n(skipping video; pass --video to make one)")


if __name__ == "__main__":
    main()
