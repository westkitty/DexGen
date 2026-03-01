#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$PROJECT_DIR/DexGenApp/.env"
APP_BUNDLE="$PROJECT_DIR/DexGenApp/dist/DexGen App.app"
LOCAL_APP_PY="$PROJECT_DIR/DexGenApp/app.py"
VENV_PY="$PROJECT_DIR/DexGenApp/venv/bin/python"

WAIT_SECONDS="${DEXGEN_LAUNCH_TIMEOUT:-900}"
POLL_SECONDS=5

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "DexGen Launcher"
echo "==============="

if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Missing .env file: $ENV_FILE${NC}"
    exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${COLAB_URL:-}" ]] || [[ "${COLAB_URL}" == *"YOUR_COLAB_ID_HERE"* ]]; then
    echo -e "${RED}Set COLAB_URL in $ENV_FILE first.${NC}"
    exit 1
fi

echo -e "${YELLOW}Opening Colab...${NC}"
open "$COLAB_URL"
echo "Action required: in Colab click Runtime > Run all."
echo "Waiting for backend readiness from Google Drive rendezvous..."

open_local_ui() {
    if [ -d "$APP_BUNDLE" ]; then
        echo -e "${GREEN}Opening DexGen App bundle...${NC}"
        open "$APP_BUNDLE"
        return
    fi
    if [ -x "$VENV_PY" ] && [ -f "$LOCAL_APP_PY" ]; then
        echo -e "${GREEN}App bundle missing. Starting local UI from Python...${NC}"
        cd "$PROJECT_DIR/DexGenApp"
        "$VENV_PY" "$LOCAL_APP_PY"
        return
    fi
    echo -e "${RED}No local UI launch target found.${NC}"
    echo "Expected app bundle: $APP_BUNDLE"
    echo "Or python entrypoint: $LOCAL_APP_PY"
    exit 1
}

is_backend_ready() {
    local status_json url
    status_json="$(rclone cat gdrive:DexGen/status.json 2>/dev/null || true)"
    url="$(rclone cat gdrive:DexGen/current_url.txt 2>/dev/null | tr -d '\r\n' || true)"
    if [[ -z "$status_json" || -z "$url" ]]; then
        echo "not_ready"
        return 0
    fi
    python3 - "$status_json" "$url" <<'PY'
import json
import sys
try:
    status = json.loads(sys.argv[1])
    url = sys.argv[2].strip()
    ok = bool(status.get("ok"))
    print("ready" if (ok and url.startswith("http")) else "not_ready")
except Exception:
    print("not_ready")
PY
}

if ! command -v rclone >/dev/null 2>&1; then
    echo -e "${YELLOW}rclone not found. Opening local UI now; use Refresh Backend after Colab starts.${NC}"
    open_local_ui
    exit 0
fi

deadline=$(( $(date +%s) + WAIT_SECONDS ))
while [ "$(date +%s)" -lt "$deadline" ]; do
    state="$(is_backend_ready)"
    if [ "$state" = "ready" ]; then
        echo -e "${GREEN}Backend is ready. Opening local UI...${NC}"
        open_local_ui
        exit 0
    fi
    sleep "$POLL_SECONDS"
done

echo -e "${YELLOW}Timed out waiting for backend readiness. Opening local UI anyway.${NC}"
open_local_ui
