"""Check 6 (documentation): the README matches the running system.

- the README has every main section, in order
- every local URL in the README responds
- every `make` command the README mentions is a real Makefile target
- every script and fixture photo the README mentions exists
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from _rg import Check, httpx

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
MAKEFILE = (ROOT / "Makefile").read_text(encoding="utf-8")

SECTIONS = [
    "## The problem", "## The solution", "## System architecture",
    "## How a return is reviewed", "## Governance and safety", "## Security",
    "## Machine learning", "## Monitoring", "## Edge cases handled",
    "## Tech stack", "## Project structure", "## Getting started",
    "## Deployment", "## Testing", "## Demo scenarios", "## Troubleshooting",
]


def main() -> None:
    c = Check("verify_m6")

    # every main section is there, in this order
    positions = [README.find(s) for s in SECTIONS]
    for s, p in zip(SECTIONS, positions):
        c.ok(p >= 0, f"README has '{s[3:]}'")
    found = [p for p in positions if p >= 0]
    c.ok(found == sorted(found), "README sections are in the expected order")
    for level in ["shadow", "suggest", "assist", "auto"]:
        c.ok(f"`{level}`" in README, f"README explains automation level '{level}'")

    # every local URL in the README responds (< 500)
    urls = sorted(set(re.findall(r"http://localhost:\d+[^\s|)`]*", README)))
    c.ok(len(urls) >= 8, f"README lists {len(urls)} local URLs")
    for u in urls:
        try:
            code = httpx.get(u, timeout=8, follow_redirects=True).status_code
            ok = code < 500
        except Exception as e:  # noqa: BLE001
            code, ok = f"ERR {type(e).__name__}", False
        c.ok(ok, f"{u} -> {code}")

    # every `make <target>` in the README exists
    targets = sorted(set(re.findall(r"(?:^|`)make ([a-z][a-z0-9-]*)", README, re.M)))
    for tgt in targets:
        c.ok(re.search(rf"^{re.escape(tgt)}:", MAKEFILE, re.M) is not None,
             f"Makefile has target '{tgt}'")

    # every script and fixture photo the README mentions exists
    for s in ["gen_secrets.py", "requirements.txt"]:
        c.ok((ROOT / "scripts" / s).exists(), f"scripts/{s} exists")
    for name in sorted(set(re.findall(r"`(verify_[a-z0-9_]+)`", README))):
        c.ok((ROOT / "scripts" / f"{name}.py").exists(), f"scripts/{name}.py exists")
    for photo in sorted(set(re.findall(r"`([A-Za-z0-9_-]+\.jpg)`", README))):
        c.ok((ROOT / "scripts" / "fixtures" / photo).exists(), f"scripts/fixtures/{photo} exists")
    c.ok((ROOT / "docker-compose.gpu.yml").exists(), "docker-compose.gpu.yml exists")

    c.done()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"verify_m6 crashed: {type(e).__name__}: {e}")
        sys.exit(2)
