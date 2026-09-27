"""Page through every file in your workspace and delete the ones you choose.

Files count against a storage quota, so a workspace that runs batches every
night fills up with input files nobody needs. This lists them a page at a time
and deletes the ones whose display name starts with the prefix you give. On
Vatan a file's display name is the name of the file you uploaded, so name your
batch inputs `nightly-2026-09-27.jsonl` and `--prefix nightly-` finds them.

    uv run python clean_up.py                          # list only, deletes nothing
    uv run python clean_up.py --prefix nightly- --delete

The only Vatan-specific line is the base URL on the client.
"""

from __future__ import annotations

import argparse

from google.genai import types

from manage_files import client, run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prefix", default="", help="only files whose display name (the uploaded filename) starts with this")
    parser.add_argument("--page-size", type=int, default=100, help="files per page, 1 to 100 (default 100)")
    parser.add_argument("--delete", action="store_true", help="delete them; without this nothing is removed")
    args = parser.parse_args()

    c = client()

    # ── List, a page at a time ────────────────────────────────────────────
    # `page_size` goes up to 100; ask for more and you get 100. The pager
    # follows `nextPageToken` for you, so iterating it walks every page, not
    # only the first. `pager.page` is the page you are on, if you want it.
    #
    # Collect first and delete after. Deleting while you walk the pages works
    # on Vatan, but it is a habit that skips files on APIs whose pages are
    # counted by offset, and nothing is gained by the risk.
    pager = c.files.list(config=types.ListFilesConfig(page_size=args.page_size))
    everything = list(pager)
    chosen = [f for f in everything if (f.display_name or "").startswith(args.prefix)]
    print(f"listed     {len(everything)} file(s), {len(chosen)} match prefix {args.prefix!r}")
    for f in chosen:
        print(f"             {f.name}  {f.display_name}  {f.size_bytes or 0} bytes  {f.create_time:%Y-%m-%d}")

    if not args.delete:
        print("nothing deleted; add --delete to remove these")
        return

    # ── Delete ────────────────────────────────────────────────────────────
    # A deleted file is gone from the list at once and stops counting against
    # the quota. Deleting a batch's input never costs you its answers: the
    # output file belongs to the batch.
    for f in chosen:
        c.files.delete(name=f.name)
        print(f"deleted    {f.name}")


if __name__ == "__main__":
    run(main)
