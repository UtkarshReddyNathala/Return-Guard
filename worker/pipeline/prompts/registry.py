"""Loads the agents' prompts.

The `.md` files in this folder are the source of truth in git. `make sync-prompts`
pushes any changed file to Langfuse as a new version labelled `production`, where it
is versioned, editable in the UI and linked to the traces that used it.

`load()` gets the `production` version from Langfuse, and uses the local file if
Langfuse cannot be reached or the prompt was never pushed. So the pipeline works the
same with or without Langfuse.
"""
from __future__ import annotations

import hashlib
import pathlib
from functools import lru_cache

_DIR = pathlib.Path(__file__).parent


def read_file(name: str) -> tuple[str, str]:
    """(body, file_version) from prompts/<name>.md — `version:` is the first line."""
    text = (_DIR / f"{name}.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    if lines and lines[0].lower().startswith("version:"):
        return "\n".join(lines[1:]).strip(), lines[0].split(":", 1)[1].strip()
    return text.strip(), "0"


def _lf_prompt(name: str):
    """The Langfuse prompt object for `name` (production version), or None. The file text
    is given to Langfuse as its own fallback, so a failed fetch still returns usable
    text.
    """
    try:
        from pipeline.observability import lf

        body, _ = read_file(name)
        return lf().get_prompt(name, label="production", cache_ttl_seconds=300,
                               fallback=body, max_retries=1)
    except Exception:  # noqa: BLE001 — any failure -> file path in load()
        return None


@lru_cache(maxsize=64)
def load(name: str) -> tuple[str, str, str]:
    """(body, version, sha256[:16]). `version` is `lf:<n>` when it came from
    Langfuse, else the file's `version:` header value."""
    body_file, ver_file = read_file(name)
    p = _lf_prompt(name)
    if p is not None and isinstance(getattr(p, "prompt", None), str) \
            and not getattr(p, "is_fallback", False):
        body, version = p.prompt, f"lf:{p.version}"
    else:
        body, version = body_file, ver_file
    return body, version, hashlib.sha256(body.encode()).hexdigest()[:16]


def prompt_version(name: str) -> str:
    _, v, h = load(name)
    return f"{name}.v{v}.{h}"


def langfuse_prompt(name: str):
    """The Langfuse prompt object, for linking a generation to its prompt
    version in the trace. None if Langfuse isn't reachable."""
    p = _lf_prompt(name)
    return p if (p is not None and not getattr(p, "is_fallback", False)) else None
