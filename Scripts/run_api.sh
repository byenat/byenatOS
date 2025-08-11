#!/usr/bin/env bash
set -euo pipefail

export SMALL_MODEL_MODE=${SMALL_MODEL_MODE:-true}
export ENABLE_VECTOR_INDEX=${ENABLE_VECTOR_INDEX:-false}
export ENABLE_FULLTEXT_INDEX=${ENABLE_FULLTEXT_INDEX:-false}
export REDIS_URL=${REDIS_URL:-redis://localhost:6379}
export DATABASE_URL=${DATABASE_URL:-postgresql://byenatos:byenatos@localhost:5432/byenatos}
export COLD_STORAGE_PATH=${COLD_STORAGE_PATH:-/tmp/byenatos_cold}
export CHROMA_PERSIST_DIR=${CHROMA_PERSIST_DIR:-/tmp/byenatos_chroma}
export ELASTICSEARCH_URL=${ELASTICSEARCH_URL:-http://localhost:9200}

# Install dependencies if virtualenv is present, otherwise assume user installed
if [[ -f requirements.txt ]]; then
  pip3 install -r requirements.txt
fi

# Start API
exec uvicorn InterfaceAbstraction.APIs.AppIntegrationAPI:create_app \
  --host 0.0.0.0 --port 8080 --factory