#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

WEBUI_SECRET_KEY="t0p-s3cr3t"

if [[ "${USE_OLLAMA_DOCKER,,}" == "true" ]]; then
    echo "USE_OLLAMA is set to true, starting ollama serve."
    ollama serve &
fi

if [[ "${USE_CUDA_DOCKER,,}" == "true" ]]; then
  echo "CUDA is enabled, appending LD_LIBRARY_PATH to include torch/cudnn & cublas libraries."
  export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/usr/local/lib/python3.11/site-packages/torch/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib"
fi

# Check if SPACE_ID is set, if so, configure for space
if [ -n "$SPACE_ID" ]; then
  echo "Configuring for HuggingFace Space deployment"
  if [ -n "$ADMIN_USER_EMAIL" ] && [ -n "$ADMIN_USER_PASSWORD" ]; then
    echo "Admin user configured, creating"
    WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" uvicorn main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*' &
    webui_pid=$!
    echo "Waiting for webui to start..."
    while ! curl -s http://localhost:8080/health > /dev/null; do
      sleep 1
    done
    echo "Creating admin user..."
    curl \
      -X POST "http://localhost:8080/api/v1/auths/signup" \
      -H "accept: application/json" \
      -H "Content-Type: application/json" \
      -d "{ \"email\": \"${ADMIN_USER_EMAIL}\", \"password\": \"${ADMIN_USER_PASSWORD}\", \"name\": \"Admin\" }"
    echo "Shutting down webui..."
    kill $webui_pid
  fi

  export WEBUI_URL=${SPACE_HOST}
fi

WEBUI_SECRET_KEY="$WEBUI_SECRET_KEY" exec uvicorn main:app --host "$HOST" --port "$PORT" --forwarded-allow-ips '*'
