"""Pushes every `worker/pipeline/prompts/*.md` file to Langfuse as a `production`
prompt. A new Langfuse version is only created when the file text has changed, so it
is safe to run again. Run it with `make sync-prompts` (also part of `make m4-setup`):

    docker compose run --rm worker python -m pipeline.sync_prompts
"""
from __future__ import annotations

import logging
import pathlib

from pipeline.observability import lf
from pipeline.prompts.registry import read_file

_DIR = pathlib.Path(__file__).parent / "prompts"


def _current(client, name: str) -> str | None:
    """Text of the current `production` prompt, or None if it does not exist yet.
    The SDK logs an ERROR line for the expected 404 on the first run, so ERROR logs are
    hidden for just this check (CRITICAL errors still show).
    """
    logging.disable(logging.ERROR)
    try:
        cur = client.get_prompt(name, label="production", cache_ttl_seconds=0,
                                max_retries=1)
        return cur.prompt if isinstance(cur.prompt, str) else None
    except Exception:  # noqa: BLE001 — not found yet, or a Langfuse hiccup
        return None
    finally:
        logging.disable(logging.NOTSET)


def main() -> None:
    client = lf()
    pushed = 0
    for md in sorted(_DIR.glob("*.md")):
        name = md.stem
        body, fver = read_file(name)
        cur = _current(client, name)
        if cur is not None and cur.strip() == body.strip():
            print(f"  {name}: up to date")
            continue
        p = client.create_prompt(name=name, prompt=body, type="text",
                                 labels=["production"],
                                 commit_message=f"sync from {name}.md v{fver}")
        pushed += 1
        print(f"  {name}: pushed -> lf v{p.version}")
    client.flush()
    print(f"sync_prompts: {pushed} prompt(s) pushed")


if __name__ == "__main__":
    main()
