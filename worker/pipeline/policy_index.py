"""The return-policy search index in Qdrant (the RAG part of the Policy agent).

- `reembed()` reads the active `policy_docs` rows, turns each into an embedding with
  `text-embedding-3-small` through Bifrost, and saves them in the `policy_docs` Qdrant
  collection, together with the policy version. It runs during `make m4-setup` and
  after an admin edits the policy.
- `retrieve(query)` embeds the question and returns the best-matching policy parts,
  from the version currently in force.
"""
from __future__ import annotations

import structlog
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from pipeline.settings import get_settings

log = structlog.get_logger()
COLLECTION = "policy_docs"
DIM = 1536  # text-embedding-3-small


def _qdrant() -> QdrantClient:
    return QdrantClient(url=get_settings().qdrant_url)


def _embed(texts: list[str]) -> list[list[float]]:
    s = get_settings()
    client = OpenAI(base_url=f"{s.bifrost_url}/v1", api_key="bifrost")
    resp = client.embeddings.create(model="openai/text-embedding-3-small", input=texts)
    return [d.embedding for d in resp.data]


def _ensure_collection(q: QdrantClient) -> None:
    if not q.collection_exists(COLLECTION):
        q.create_collection(COLLECTION, vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))


async def reembed() -> dict:
    from pipeline import db

    rows = await db.fetchall(
        "SELECT id::text, version, slug, title, body FROM policy_docs "
        "WHERE active = true ORDER BY version DESC, slug"
    )
    if not rows:
        return {"embedded": 0}
    # only the highest version is "in force"
    max_v = max(r["version"] for r in rows)
    live = [r for r in rows if r["version"] == max_v]

    q = _qdrant()
    _ensure_collection(q)
    q.delete_collection(COLLECTION)
    q.create_collection(COLLECTION, vectors_config=VectorParams(size=DIM, distance=Distance.COSINE))

    vecs = _embed([f"{r['title']}\n{r['body']}" for r in live])
    points = [
        PointStruct(
            id=i,
            vector=v,
            payload={"policy_version": r["version"], "slug": r["slug"],
                     "title": r["title"], "body": r["body"]},
        )
        for i, (r, v) in enumerate(zip(live, vecs, strict=True))
    ]
    q.upsert(COLLECTION, points)
    await db.execute("UPDATE policy_docs SET embedded_at = now() WHERE version = %(v)s",
                     {"v": max_v})
    log.info("policy_index.reembed", version=max_v, chunks=len(points))
    return {"embedded": len(points), "policy_version": max_v}


def retrieve(query: str, k: int = 3) -> tuple[list[dict], int | None]:
    q = _qdrant()
    if not q.collection_exists(COLLECTION):
        return [], None
    qv = _embed([query])[0]
    hits = q.query_points(COLLECTION, query=qv, limit=k, with_payload=True).points
    docs = [
        {"slug": h.payload["slug"], "title": h.payload["title"],
         "body": h.payload["body"], "score": round(h.score, 4)}
        for h in hits
    ]
    version = hits[0].payload["policy_version"] if hits else None
    return docs, version


if __name__ == "__main__":
    import asyncio

    from pipeline import db

    async def _main():
        await db.start()
        print(await reembed())
        docs, v = retrieve("item returned 40 days after delivery")
        print("version", v)
        for d in docs:
            print(" -", d["slug"], d["score"])
        await db.stop()

    asyncio.run(_main())
