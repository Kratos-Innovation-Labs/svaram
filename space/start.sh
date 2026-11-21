#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
#
# Start the Svaram demo inside the Hugging Face Space container (see space/Dockerfile).
#
#   1. download every model from its publisher and check each file's SHA-256 (tools/fetch_models.py)
#   2. start the same five services svaram.live runs, each in its own locked Python environment,
#      with the same settings deploy/install.sh writes
#   3. wait until each one says it is ready, then start the Gradio page on port 7860
#
# HF_TOKEN (a read-only token kept as a private Space secret) is used only to download the gated
# IndicTrans2 model, and is removed from the environment before any service starts.
set -euo pipefail
cd "${SVARAM_SRC:?}"
M="$HOME/models"
say() { echo "[svaram-space $(date -u +%H:%M:%S)] $*"; }
pin() { /opt/venv/voice/bin/python -c "import yaml,sys; d=yaml.safe_load(open('deploy/models.yaml')); print(d[sys.argv[1]]['files'][sys.argv[2]]['sha256'])" "$1" "$2"; }

# ------------------------------------------------------------------ 1. models
[ -n "${HF_TOKEN:-}" ] || say "warning: no HF_TOKEN secret is set; the IndicTrans2 download will be refused"
mkdir -p "$M"
ok=0
for attempt in 1 2 3; do
  say "models: downloading and checking (attempt $attempt)"
  if /opt/venv/voice/bin/python -u tools/fetch_models.py rasa kokoro translate indictts \
       --models-root "$M" --indictts-langs gu,or --manifest-sha-out "$M/itts.sha" \
       --itts-python /opt/venv/voice-itts/bin/python; then ok=1; break; fi
  sleep $((attempt * 20))
done
unset HF_TOKEN
[ $ok = 1 ] || { say "STOP: the models could not be downloaded and checked"; exit 1; }

# ------------------------------------------------------------------ 2. services
UV=(--host 127.0.0.1 --workers 1 --no-access-log --log-level warning --no-server-header)

env SVARAM_TRANSLATE_MODEL_DIR="$M/translate/model" \
    SVARAM_TRANSLATE_MODEL_SHA256="$(pin translate model.safetensors)" \
    SVARAM_TRANSLATE_THREADS=2 SVARAM_TRANSLATE_BEAMS=1 SVARAM_TRANSLATE_INT8=0 \
    SVARAM_TRANSLATE_USE_CACHE=1 SVARAM_TRANSLATE_MAX_CHARS=500 \
    SVARAM_TRANSLATE_QUEUE=4 SVARAM_TRANSLATE_QUEUE_WAIT_MS=4000 \
  /opt/venv/translate/bin/uvicorn svaram_translate:app --app-dir translate --port 8201 "${UV[@]}" &

env SVARAM_VOICE_ENGINE=vits_rasa SVARAM_VOICE_MODEL_DIR="$M/voice/model" \
    SVARAM_MODEL_SHA256="$(pin rasa model.onnx)" \
    SVARAM_VOICE_THREADS=2 SVARAM_VOICE_CONCURRENCY=1 SVARAM_VOICE_QUEUE=2 \
    SVARAM_VOICE_QUEUE_WAIT_MS=800 SVARAM_VOICE_MAX_CHARS=400 SVARAM_VOICE_MP3_KBPS=48 \
  /opt/venv/voice/bin/uvicorn svaram_voice:app --app-dir voices/rasa --port 8199 "${UV[@]}" &

env SVARAM_VOICE_HI_MODEL_DIR="$M/voice-hi/model" SVARAM_VOICE_HI_MODEL=kokoro-v1.0.onnx \
    SVARAM_VOICE_HI_MODEL_SHA256="$(pin kokoro kokoro-v1.0.onnx)" \
    SVARAM_VOICE_HI_VOICES_SHA256="$(pin kokoro voices-v1.0.bin)" \
    SVARAM_VOICE_HI_THREADS=2 SVARAM_VOICE_HI_QUEUE=2 SVARAM_VOICE_HI_QUEUE_WAIT_MS=1200 \
    SVARAM_VOICE_HI_MAX_CHARS=400 \
  /opt/venv/voice-hi/bin/uvicorn svaram_voice_hi:app --app-dir voices/kokoro --port 8202 "${UV[@]}" &

env SVARAM_VOICE_ITTS_MODEL_DIR="$M/voice-itts/model" \
    SVARAM_VOICE_ITTS_MANIFEST_SHA256="$(cat "$M/itts.sha")" SVARAM_VOICE_ITTS_LANGS=gu,or \
    SVARAM_VOICE_ITTS_THREADS=2 SVARAM_VOICE_ITTS_QUEUE=2 SVARAM_VOICE_ITTS_QUEUE_WAIT_MS=1500 \
    SVARAM_VOICE_ITTS_MAX_CHARS=400 SVARAM_VOICE_ITTS_PIECE=60 MPLCONFIGDIR="$HOME/.mpl" \
  /opt/venv/voice-itts/bin/uvicorn svaram_voice_itts:app --app-dir voices/indictts --port 8203 "${UV[@]}" &

ready() {   # name port path seconds
  for ((i = 0; i < $4; i += 3)); do
    if curl -fsS --max-time 3 "http://127.0.0.1:$2/$3" 2>/dev/null | grep -q '"status": *"ok"'; then
      say "$1 ready"; return 0
    fi
    sleep 3
  done
  say "STOP: $1 did not become ready"; exit 1
}
ready voice 8199 health 180
ready voice-hi 8202 health 180
ready translate 8201 health 420
ready voice-itts 8203 health 600

env SVARAM_API_MAX_TEXT=300 SVARAM_API_SEG_CAP=200 SVARAM_API_VOICE_TIMEOUT_S=20 \
    SVARAM_API_TRANSLATE_TIMEOUT_S=30 \
  /opt/venv/voice/bin/uvicorn svaram_api:app --app-dir api --port 8200 "${UV[@]}" &
ready api 8200 api/health 60

# ------------------------------------------------------------------ 3. the page
say "starting the page on port 7860"
exec env GRADIO_ANALYTICS_ENABLED=False /opt/venv/space/bin/python -u space/app.py
