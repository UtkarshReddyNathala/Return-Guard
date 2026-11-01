#!/usr/bin/env bash
# Backs up all data into backups/<timestamp>/: a Postgres dump (pg_dump), a Qdrant
# snapshot and a copy of every MinIO file. Restore it with scripts/restore.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
TS=$(date +%Y%m%d-%H%M%S)
OUT="backups/$TS"
mkdir -p "$OUT"

echo "[backup] postgres"
docker compose exec -T postgres pg_dump -U returnguard -Fc returnguard > "$OUT/returnguard.dump"

echo "[backup] qdrant snapshot"
curl -s -X POST "http://localhost:6333/collections/policy_docs/snapshots" >/dev/null || true
NAME=$(curl -s "http://localhost:6333/collections/policy_docs/snapshots" \
  | python -c "import sys,json;d=json.load(sys.stdin);print(d['result'][-1]['name'])" 2>/dev/null || echo "")
if [ -n "$NAME" ]; then
  curl -s "http://localhost:6333/collections/policy_docs/snapshots/$NAME" -o "$OUT/qdrant-policy_docs.snapshot"
fi

echo "[backup] minio mirror"
# Copy the MinIO files inside a named container, then `docker cp` them out and remove
# the container. Mounting a host folder into `compose run` is unreliable on Windows
# Docker Desktop (drive letters and spaces in paths), so copying is used instead.
CID="rg-backup-mc-$TS"
docker compose run -T --name "$CID" --entrypoint sh minio-init -c \
  "mc alias set l http://minio:9000 \$MINIO_ROOT_USER \$MINIO_ROOT_PASSWORD >/dev/null && mc mirror --overwrite l/returnguard /tmp/mirror"
docker cp "$CID:/tmp/mirror" "$OUT/minio"
docker rm -f "$CID" >/dev/null
echo "[backup] minio objects: $(find "$OUT/minio" -type f | wc -l)"

echo "[backup] done -> $OUT"
