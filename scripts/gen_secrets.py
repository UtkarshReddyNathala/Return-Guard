"""Creates all local secrets for a fresh checkout.

It writes `.env` from `.env.example` and `frontend/.env.local` from its example, and
fills every generated password or key with a new random value. Values that are
already set are left as they are, so running it again never breaks a working stack.
The two paid API keys are never touched; you add those yourself.

    python scripts/gen_secrets.py

Formats that matter:
  * LANGFUSE_ENCRYPTION_KEY  exactly 64 hex characters (an AES-256 key)
  * LANGFUSE_INIT_PROJECT_*  pk-lf-... / sk-lf-... (Langfuse's format)
  * everything else          a 32-character URL-safe random string
"""
from __future__ import annotations

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# field -> how to mint it. Anything not listed is copied through unchanged.
GEN = {
    "POSTGRES_PASSWORD": lambda: secrets.token_urlsafe(24),
    "MINIO_ROOT_PASSWORD": lambda: secrets.token_urlsafe(24),
    "KEYCLOAK_ADMIN_PASSWORD": lambda: secrets.token_urlsafe(18),
    "LANGFUSE_SALT": lambda: secrets.token_urlsafe(24),
    "LANGFUSE_NEXTAUTH_SECRET": lambda: secrets.token_urlsafe(32),
    "NEXTAUTH_SECRET": lambda: secrets.token_urlsafe(32),
    "CONTEXTFORGE_JWT_SECRET": lambda: secrets.token_urlsafe(32),
    "BIFROST_ADMIN_TOKEN": lambda: secrets.token_urlsafe(32),
    "LANGFUSE_ENCRYPTION_KEY": lambda: secrets.token_hex(32),
    "LANGFUSE_INIT_PROJECT_SECRET_KEY": lambda: "sk-lf-" + secrets.token_urlsafe(32),
    "LANGFUSE_INIT_PROJECT_PUBLIC_KEY": lambda: "pk-lf-" + secrets.token_urlsafe(32),
}
API_KEYS = ("OPENAI_API_KEY", "GROQ_API_KEY")


def _fill(example: Path, target: Path) -> tuple[int, int]:
    """Write `target` from `example`, filling in blank values. Returns (generated, kept)."""
    src = target if target.exists() else example
    generated = kept = 0
    out: list[str] = []
    for line in src.read_text().splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            out.append(line)
            continue
        key, _, val = s.partition("=")
        key, val = key.strip(), val.strip()
        if val:
            kept += 1
            out.append(f"{key}={val}")
        elif key in GEN:
            generated += 1
            out.append(f"{key}={GEN[key]()}")
        else:
            out.append(f"{key}={val}")  # left blank on purpose (API keys, etc.)
    target.write_text("\n".join(out) + "\n")
    return generated, kept


def main() -> None:
    env_ex = ROOT / ".env.example"
    env = ROOT / ".env"
    fe_ex = ROOT / "frontend" / ".env.local.example"
    fe = ROOT / "frontend" / ".env.local"

    g1, k1 = _fill(env_ex, env)
    # frontend AUTH_SECRET isn't in GEN's list — mint it here if still blank
    GEN["AUTH_SECRET"] = lambda: secrets.token_urlsafe(32)
    g2, k2 = _fill(fe_ex, fe)

    print(f".env               : {g1} generated, {k1} kept")
    print(f"frontend/.env.local: {g2} generated, {k2} kept")
    missing = [k for k in API_KEYS
               if not any(l.startswith(f"{k}=") and l.strip() != f"{k}="
                          for l in env.read_text().splitlines())]
    if missing:
        print("\nStill blank - set these by hand in .env before `make up`:")
        for k in missing:
            print(f"  {k}")


if __name__ == "__main__":
    main()
