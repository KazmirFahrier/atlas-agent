# Deploying Atlas to GCP Cloud Run

The orchestrator ships an HTTP wrapper (`orchestrator/serve.py`) exposing
`POST /ask` and `GET /healthz`, so it runs unmodified on Cloud Run.

## One-time setup

```bash
gcloud config set project YOUR_PROJECT
gcloud services enable run.googleapis.com artifactregistry.googleapis.com
gcloud secrets create atlas-anthropic-key --data-file=- <<< "$ANTHROPIC_API_KEY"
```

## Build & deploy

```bash
gcloud run deploy atlas-agent \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-secrets ANTHROPIC_API_KEY=atlas-anthropic-key:latest \
  --set-env-vars ATLAS_MODEL=claude-sonnet-4-5
```

Cloud Run injects `$PORT`; the Dockerfile's `CMD` already binds to it and the
image seeds the DuckDB warehouse at build time.

## Smoke test the deployment

```bash
URL=$(gcloud run services describe atlas-agent --region us-east1 --format='value(status.url)')
curl -s "$URL/healthz"
curl -s -X POST "$URL/ask" -H 'Content-Type: application/json' \
  -d '{"question":"Total spend by campaign last quarter"}' | jq .
```

## Moving from DuckDB to BigQuery (production)

Swap `mcp_servers/sql_exec/server.py` to use the BigQuery client and point it at
a dataset; the read-only guard and row cap carry over unchanged. This aligns
with the target stack (BigQuery / dbt / semantic layer).

## Notes

* Persistent memory (`SqliteMemoryStore`) is per-instance on Cloud Run; for
  multi-instance use, back it with Cloud SQL or Memorystore (Redis).
* The Python sandbox uses POSIX rlimits. For untrusted code at scale, run the
  py-sandbox server as a separate Cloud Run job wrapped in gVisor.
