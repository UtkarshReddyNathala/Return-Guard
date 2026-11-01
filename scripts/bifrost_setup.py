"""Creates one Bifrost virtual key per agent. A **virtual key** is an agent's own key
for the LLM gateway, with its own limits:
  - `allowed_models`: the models it may call (Bifrost rejects any other model),
  - a monthly budget in US dollars,
  - a rate limit per minute.

The key values are saved in Vault (`secret/returnguard/bifrost` -> `agent_keys`).
They are only sent with model calls when `RG_USE_BIFROST_VK=1`. By default this is
off, because OSS Bifrost v2.0.0 cannot link a virtual key to provider keys that come
from env or config files. The per-agent model limits are still enforced, in
`worker/pipeline/models_config.py` and OPA (`infra/opa/authz.rego`).

Run: python scripts/bifrost_setup.py
"""
from __future__ import annotations

import json
import subprocess

from _rg import BIFROST, httpx

# agent -> (groq models, openai models) it may use, mirroring AGENT_MODEL_GRANTS
GRANTS = {
    "planner": (["openai/gpt-oss-20b"], ["gpt-4o-mini"]),
    "intake": (["openai/gpt-oss-20b"], ["gpt-4o-mini"]),
    "policy": (["openai/gpt-oss-120b"], ["gpt-4o-mini", "text-embedding-3-small"]),
    "image": ([], ["gpt-4o", "gpt-4o-mini"]),
    "behavior": (["openai/gpt-oss-120b"], ["gpt-4o-mini"]),
    "decision": (["openai/gpt-oss-120b"], ["gpt-4o-mini"]),
    "critic": ([], ["gpt-4o-mini", "gpt-4o"]),
    "explanation": ([], ["gpt-4o-mini"]),
}
BUDGET_USD = 3.0
RPM = 60
TPM = 200_000


def main() -> None:
    # Bifrost only shows a virtual key's value when it is created, so delete and
    # recreate each key. This makes the script safe to re-run and captures every value.
    r = httpx.get(f"{BIFROST}/api/governance/virtual-keys", timeout=15).json()
    for v in r.get("virtual_keys") or []:
        if v["name"].startswith("agent-"):
            httpx.delete(f"{BIFROST}/api/governance/virtual-keys/{v['id']}", timeout=15)

    values: dict[str, str] = {}
    for agent, (groq_models, oai_models) in GRANTS.items():
        name = f"agent-{agent}"
        pcfgs = []
        if groq_models:
            pcfgs.append({"provider": "groq", "allow_all_keys": True, "allowed_models": groq_models})
        if oai_models:
            pcfgs.append({"provider": "openai", "allow_all_keys": True, "allowed_models": oai_models})
        body = {
            "name": name,
            "description": f"ReturnGuard {agent} agent",
            "provider_configs": pcfgs,
            "budget": {"max_limit": BUDGET_USD, "reset_duration": "1M"},
            "rate_limit": {"token_max_limit": TPM, "token_reset_duration": "1m",
                           "request_max_limit": RPM, "request_reset_duration": "1m"},
        }
        resp = httpx.post(f"{BIFROST}/api/governance/virtual-keys", json=body, timeout=15)
        resp.raise_for_status()
        vk = resp.json()["virtual_key"]
        values[agent] = vk["value"]
        print(f"  {name} -> {vk['value'][:16]}...  "
              f"groq={groq_models} openai={oai_models}  ${BUDGET_USD}/mo  {RPM}rpm")

    _to_vault(values)
    print("\nPer-agent Bifrost virtual keys = the model-scope + budget + rate-limit layer.")
    print("Model least-privilege is also enforced in worker/pipeline/models_config.py.")
    print("Send VKs on the inference hot path with RG_USE_BIFROST_VK=1.")


def _to_vault(values: dict[str, str]) -> None:
    r = subprocess.run(
        ["docker", "compose", "exec", "-T", "-e", "VAULT_ADDR=http://vault:8200",
         "-e", "VAULT_TOKEN=root", "vault", "vault", "kv", "put",
         "secret/returnguard/bifrost", f"agent_keys={json.dumps(values)}"],
        capture_output=True, text=True,
    )
    print("vault:", "ok" if r.returncode == 0 else r.stderr[:200])


if __name__ == "__main__":
    main()
