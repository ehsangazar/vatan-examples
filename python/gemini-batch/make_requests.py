"""Write the batch input file.

One JSON object per line, each with a `key` you choose and a `request` that is an
ordinary Gemini GenerateContentRequest. The model is not in the line: it is named once,
on the job, when the batch is created.

`maxOutputTokens` is on every request on purpose. Vatan checks a batch against your
balance before sending it, and the worst case cannot be worked out without a bound on
the output, so a request without one is refused when the batch is created.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "reviews.jsonl"

# Stand-ins for whatever you actually have a lot of: support tickets, product reviews,
# survey answers, log lines. The batch API earns its keep somewhere around a thousand.
SUBJECTS = ["the delivery", "the packaging", "the app", "support", "the price", "setup"]
OPINIONS = [
    "was excellent, no notes",
    "took three weeks and arrived damaged",
    "did the job",
    "is the best I have used",
    "made me give up and buy elsewhere",
    "was fine until it broke",
    "is far better than it was last year",
    "is confusing and nobody replied",
]

PROMPT = (
    "Classify this customer review. Answer with one word only, chosen from: "
    "positive, negative, mixed.\n\nReview: {review}"
)


def main(count: int = 3000, seed: int = 7) -> None:
    random.seed(seed)
    with OUT.open("w") as f:
        for i in range(1, count + 1):
            review = f"{random.choice(SUBJECTS).capitalize()} {random.choice(OPINIONS)}."
            f.write(
                json.dumps(
                    {
                        # Your own name for this request. It comes back on the answer,
                        # which is how you match results to inputs: the order is not
                        # guaranteed and should not be relied on.
                        "key": f"review-{i}",
                        "request": {
                            "contents": [
                                {"role": "user", "parts": [{"text": PROMPT.format(review=review)}]}
                            ],
                            "generationConfig": {"maxOutputTokens": 8, "temperature": 0},
                        },
                    }
                )
                + "\n"
            )

    size = OUT.stat().st_size
    print(f"wrote {OUT.name}: {count:,} requests, {size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
