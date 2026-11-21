#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Kratos Innovation Labs Limited
#
# Install Svaram on one Ubuntu 24.04 server.
#
#   sudo bash deploy/install.sh                              # every language in web/site.yaml, no web server
#   sudo bash deploy/install.sh --languages te,hi            # only these languages (and only their voices)
#   sudo bash deploy/install.sh --domain svaram.example.org  # also set up nginx for that domain
#
# What it does: checks the machine, installs system packages, creates one system user and one
# Python environment per service (exact versions from deploy/requirements/), downloads only the
# models the chosen languages need and checks each file's SHA-256, writes /etc/svaram/*.env,
# installs hardened systemd units, starts the services, builds the pages, makes the phrase audio,
# and runs tools/selftest.py. Running it again is safe: finished steps are checked and skipped.
#
# Nothing a person types is ever logged. Models are never copied into this repository.
set -euo pipefail

SRC_IN="$(cd "$(dirname "$0")/.." && pwd)"
LANGS=""
DOMAIN=""
SKIP_PHRASES=0
while [ $# -gt 0 ]; do
  case "$1" in
    --languages) LANGS="$2"; shift 2 ;;
    --domain) DOMAIN="$2"; shift 2 ;;
    --skip-phrases) SKIP_PHRASES=1; shift ;;
    -h|--help) sed -n '4,18p' "$0"; exit 0 ;;
    *) echo "unknown option $1 (see --help)"; exit 1 ;;
  esac
done
say() { echo "[svaram-install $(date -u +%H:%M:%S)] $*"; }
die() { say "STOP: $*"; exit 1; }
[ "$(id -u)" = 0 ] || die "run with sudo"

# ------------------------------------------------------------------ 1. the machine
say "1/9 checking the machine"
. /etc/os-release
[ "${ID:-}" = ubuntu ] || say "   warning: tested on Ubuntu 24.04, this is ${PRETTY_NAME:-unknown}"
command -v python3 >/dev/null || die "python3 is missing"
for p in 8199 8200 8201 8202 8203; do
  if ss -ltnH "sport = :$p" 2>/dev/null | grep -q . && ! systemctl is-active --quiet "$(case $p in 8199) echo svaram-voice;; 8200) echo svaram-api;; 8201) echo svaram-translate;; 8202) echo svaram-voice-hi;; 8203) echo svaram-voice-itts;; esac)"; then
    die "port $p is already used by another program"
  fi
done

apt-get update -qq >/dev/null
apt-get install -y -qq python3-venv python3-pip python3-yaml curl unzip >/dev/null
[ -n "$DOMAIN" ] && apt-get install -y -qq nginx >/dev/null

# the languages and the services they need
cd "$SRC_IN"
[ -n "$LANGS" ] || LANGS=$(python3 -c "import yaml; print(','.join(yaml.safe_load(open('web/site.yaml'))['languages']))")
read -r NEED TRANSLATE ITTS_LANGS < <(python3 - "$LANGS" <<'EOF'
import sys, yaml
codes = sys.argv[1].split(",")
svc, tr, itts = set(), False, []
for c in codes:
    m = yaml.safe_load(open(f"lang/{c}/language.yaml"))
    s = m["voice"]["service"]; svc.add(s)
    tr = tr or bool(m.get("translate_target"))
    if s == "indictts": itts.append(c)
print(",".join(sorted(svc)), "yes" if tr else "no", ",".join(itts) or "-")
EOF
)
say "   languages: $LANGS"
say "   voice services: $NEED; translation: $TRANSLATE"

declare -A MEM=([rasa]=600 [kokoro]=700 [indictts]=2200 [translate]=1700)   # MB per service: estimates with some margin
declare -A DISK=([rasa]=1 [kokoro]=1 [indictts]=6 [translate]=8)
declare -A UNIT=([rasa]=svaram-voice [kokoro]=svaram-voice-hi [indictts]=svaram-voice-itts [translate]=svaram-translate)
need_mem=300; need_disk=2                    # svaram-api and the system's own margin
systemctl is-active --quiet svaram-api && need_mem=0
# a service that is already running already has its memory: count only the ones still to start
for s in ${NEED//,/ } $([ "$TRANSLATE" = yes ] && echo translate); do
  need_disk=$((need_disk + DISK[$s]))
  systemctl is-active --quiet "${UNIT[$s]}" || need_mem=$((need_mem + MEM[$s]))
done
avail=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
disk=$(df -BG --output=avail /opt | tail -1 | tr -dc 0-9)
say "   memory: need about $need_mem MB, available $avail MB; disk: need about ${need_disk} GB, free ${disk} GB"
[ "$avail" -ge "$need_mem" ] || die "not enough free memory; choose fewer languages with --languages"
[ "$disk" -ge "$need_disk" ] || die "not enough disk space under /opt"

# Svaram's locked package versions need Python 3.12. Use the system's if it is 3.12; otherwise
# fetch a private copy with uv (from PyPI) into /opt/svaram/python, leaving the system Python alone.
PY312=""
for c in python3.12 /usr/bin/python3.12; do command -v "$c" >/dev/null && PY312=$(command -v "$c") && break; done
if [ -z "$PY312" ] && [ -x /opt/svaram/tools/uv/bin/uv ]; then
  PY312=$(UV_PYTHON_INSTALL_DIR=/opt/svaram/python /opt/svaram/tools/uv/bin/uv python find 3.12 2>/dev/null || true)
fi
if [ -z "$PY312" ] || ! "$PY312" -m venv --help >/dev/null 2>&1; then
  say "   this machine has no Python 3.12: installing a private copy in /opt/svaram/python"
  mkdir -p /opt/svaram/tools /opt/svaram/python
  [ -x /opt/svaram/tools/uv/bin/uv ] || { python3 -m venv /opt/svaram/tools/uv && /opt/svaram/tools/uv/bin/pip install --quiet "uv>=0.5"; }
  UV_PYTHON_INSTALL_DIR=/opt/svaram/python /opt/svaram/tools/uv/bin/uv python install 3.12 >/dev/null
  PY312=$(UV_PYTHON_INSTALL_DIR=/opt/svaram/python /opt/svaram/tools/uv/bin/uv python find 3.12 2>/dev/null)
  chmod -R go=rX /opt/svaram/python
fi
say "   Python for Svaram: $PY312 ($("$PY312" --version 2>&1))"

# ------------------------------------------------------------------ 2. code
say "2/9 code in /opt/svaram/src"
REL=/opt/svaram/releases/$(date -u +%Y%m%d-%H%M%S)
if [ "$SRC_IN" != "$(readlink -f /opt/svaram/src 2>/dev/null || true)" ]; then
  mkdir -p /opt/svaram/releases
  cp -a "$SRC_IN" "$REL"
  rm -rf "$REL/.git"
  chown -R root:root "$REL"; chmod -R u=rwX,go=rX "$REL"
  ln -sfn "$REL" /opt/svaram/src
fi
SRC=/opt/svaram/src

# ------------------------------------------------------------------ 3. users
say "3/9 service users"
SERVICES=(svaram-api)
for s in ${NEED//,/ }; do case $s in rasa) SERVICES+=(svaram-voice);; kokoro) SERVICES+=(svaram-voice-hi);; indictts) SERVICES+=(svaram-voice-itts);; esac; done
[ "$TRANSLATE" = yes ] && SERVICES+=(svaram-translate)
[[ " ${SERVICES[*]} " == *" svaram-voice "* ]] || SERVICES+=(svaram-voice)   # svaram-api runs in the rasa environment
for u in "${SERVICES[@]}"; do
  id -u "$u" >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin "$u"
done

# ------------------------------------------------------------------ 4. python environments
say "4/9 Python environments (exact versions; the first run takes a while)"
venv() {   # folder lockfile
  local d=/opt/svaram/$1/venv
  if [ -x "$d/bin/python" ] && [ "$("$d/bin/python" -c 'import sys; print(sys.version_info[:2] == (3, 12))')" != True ]; then
    say "   $1: rebuilding (made with another Python version)"; rm -rf "$d"
  fi
  if [ ! -x "$d/bin/python" ]; then "$PY312" -m venv "$d"; fi
  "$d/bin/pip" install --quiet --upgrade pip >/dev/null
  "$d/bin/pip" install --quiet -r "$SRC/deploy/requirements/$2.lock"
  say "   $1: ready"
}
venv voice rasa
[[ ",$NEED," == *",kokoro,"* ]] && venv voice-hi kokoro
[[ ",$NEED," == *",indictts,"* ]] && venv voice-itts indictts
[ "$TRANSLATE" = yes ] && venv translate translate

# ------------------------------------------------------------------ 5. models
say "5/9 models (downloaded from their publishers, every file checked)"
FETCH=(env PYTHONUNBUFFERED=1 /opt/svaram/voice/venv/bin/python "$SRC/tools/fetch_models.py")
fetch_list=""
for s in ${NEED//,/ }; do fetch_list="$fetch_list $s"; done
[ "$TRANSLATE" = yes ] && fetch_list="$fetch_list translate"
ITTS_SHA_FILE=$(mktemp)
"${FETCH[@]}" $fetch_list --indictts-langs "${ITTS_LANGS/-/}" --manifest-sha-out "$ITTS_SHA_FILE" --itts-python /opt/svaram/voice-itts/venv/bin/python
for d in voice voice-hi voice-itts translate; do
  [ -d /opt/svaram/$d/model ] && chmod -R go=rX /opt/svaram/$d/model
done

# ------------------------------------------------------------------ 6. settings
say "6/9 settings in /etc/svaram (existing files are kept)"
mkdir -p /etc/svaram
put_env() {   # file content; never overwrites what an operator set
  local f=/etc/svaram/$1
  if [ -f "$f" ]; then say "   $1: kept"; else printf '%s\n' "$2" > "$f"; chmod 644 "$f"; say "   $1: written"; fi
}
put_env api.env "# svaram-api: every value has a default; see deploy/env/api.env.sample.
SVARAM_API_MAX_TEXT=500
SVARAM_API_SEG_CAP=200
SVARAM_API_VOICE_TIMEOUT_S=12"
put_env voice.env "SVARAM_VOICE_ENGINE=vits_rasa
SVARAM_VOICE_MODEL_DIR=/opt/svaram/voice/model
SVARAM_MODEL_SHA256=$(python3 -c "import yaml;print(yaml.safe_load(open('$SRC/deploy/models.yaml'))['rasa']['files']['model.onnx']['sha256'])")
SVARAM_VOICE_THREADS=2
SVARAM_VOICE_CONCURRENCY=1
SVARAM_VOICE_QUEUE=2
SVARAM_VOICE_QUEUE_WAIT_MS=800
SVARAM_VOICE_MAX_CHARS=400
SVARAM_VOICE_MP3_KBPS=48"
if [[ ",$NEED," == *",kokoro,"* ]]; then
put_env voice-hi.env "SVARAM_VOICE_HI_MODEL_DIR=/opt/svaram/voice-hi/model
SVARAM_VOICE_HI_MODEL=kokoro-v1.0.onnx
SVARAM_VOICE_HI_MODEL_SHA256=$(python3 -c "import yaml;print(yaml.safe_load(open('$SRC/deploy/models.yaml'))['kokoro']['files']['kokoro-v1.0.onnx']['sha256'])")
SVARAM_VOICE_HI_VOICES_SHA256=$(python3 -c "import yaml;print(yaml.safe_load(open('$SRC/deploy/models.yaml'))['kokoro']['files']['voices-v1.0.bin']['sha256'])")
SVARAM_VOICE_HI_THREADS=2
SVARAM_VOICE_HI_QUEUE=2
SVARAM_VOICE_HI_QUEUE_WAIT_MS=1200
SVARAM_VOICE_HI_MAX_CHARS=400"
fi
if [[ ",$NEED," == *",indictts,"* ]]; then
  ITTS_SHA=$(cat "$ITTS_SHA_FILE")
  if [ -f /etc/svaram/voice-itts.env ]; then
    sed -i "s/^SVARAM_VOICE_ITTS_MANIFEST_SHA256=.*/SVARAM_VOICE_ITTS_MANIFEST_SHA256=$ITTS_SHA/" /etc/svaram/voice-itts.env
  fi
put_env voice-itts.env "SVARAM_VOICE_ITTS_MODEL_DIR=/opt/svaram/voice-itts/model
SVARAM_VOICE_ITTS_MANIFEST_SHA256=$ITTS_SHA
SVARAM_VOICE_ITTS_LANGS=$ITTS_LANGS
SVARAM_VOICE_ITTS_THREADS=2
SVARAM_VOICE_ITTS_QUEUE=2
SVARAM_VOICE_ITTS_QUEUE_WAIT_MS=1500
SVARAM_VOICE_ITTS_MAX_CHARS=400
SVARAM_VOICE_ITTS_PIECE=60"
fi
rm -f "$ITTS_SHA_FILE"
if [ "$TRANSLATE" = yes ]; then
put_env translate.env "SVARAM_TRANSLATE_MODEL_DIR=/opt/svaram/translate/model
SVARAM_TRANSLATE_MODEL_SHA256=$(python3 -c "import yaml;print(yaml.safe_load(open('$SRC/deploy/models.yaml'))['translate']['files']['model.safetensors']['sha256'])")
SVARAM_TRANSLATE_THREADS=2
SVARAM_TRANSLATE_BEAMS=1
SVARAM_TRANSLATE_INT8=0
SVARAM_TRANSLATE_USE_CACHE=1
SVARAM_TRANSLATE_MAX_CHARS=500
SVARAM_TRANSLATE_QUEUE=4
SVARAM_TRANSLATE_QUEUE_WAIT_MS=4000"
fi

# ------------------------------------------------------------------ 7. services
say "7/9 systemd services"
declare -A PORT=([svaram-api]=8200 [svaram-voice]=8199 [svaram-translate]=8201 [svaram-voice-hi]=8202 [svaram-voice-itts]=8203)
declare -A WAIT=([svaram-api]=60 [svaram-voice]=120 [svaram-translate]=300 [svaram-voice-hi]=120 [svaram-voice-itts]=420)
ORDER=(svaram-translate svaram-voice svaram-voice-hi svaram-voice-itts svaram-api)
for s in "${ORDER[@]}"; do
  [[ " ${SERVICES[*]} " == *" $s "* ]] || continue
  install -m 644 "$SRC/deploy/systemd/$s.service" /etc/systemd/system/$s.service
done
systemctl daemon-reload
for s in "${ORDER[@]}"; do
  [[ " ${SERVICES[*]} " == *" $s "* ]] || continue
  systemctl enable --quiet "$s"; systemctl restart "$s"
  path=health; [ "$s" = svaram-api ] && path=api/health
  ok=0
  for ((i=0; i<${WAIT[$s]}; i+=3)); do
    if curl -fsS --max-time 3 "http://127.0.0.1:${PORT[$s]}/$path" 2>/dev/null | grep -q '"status": *"ok"'; then ok=1; break; fi
    sleep 3
  done
  [ $ok = 1 ] || { journalctl -u "$s" -n 25 --no-pager; die "$s did not become ready"; }
  say "   $s ready"
done

# ------------------------------------------------------------------ 8. pages and phrases
say "8/9 pages and phrase audio"
WEB=/var/www/svaram
SITE_TMP=$(mktemp -d)
cp -a "$SRC/web/." "$SITE_TMP/"
/opt/svaram/voice/venv/bin/python - "$SITE_TMP/site.yaml" "$LANGS" "$DOMAIN" <<'EOF'
import sys, yaml
p, langs, dom = sys.argv[1], sys.argv[2].split(","), sys.argv[3]
s = yaml.safe_load(open(p))
s["languages"] = [c for c in s["languages"] if c in langs] + [c for c in langs if c not in s["languages"]]
if s["default_language"] not in s["languages"]: s["default_language"] = s["languages"][0]
if dom: s["domain"] = dom
else: s["allow_search"] = False
yaml.safe_dump(s, open(p, "w"), allow_unicode=True, sort_keys=False)
EOF
mkdir -p "$WEB"
SVARAM_SITE_YAML="$SITE_TMP/site.yaml" /opt/svaram/voice/venv/bin/python "$SRC/tools/build_site.py" --out "$WEB.new" --check
[ -d "$WEB/phrases" ] && mv "$WEB/phrases" "$WEB.new/phrases"
rm -rf "$WEB.old"; [ -d "$WEB" ] && mv "$WEB" "$WEB.old"; mv "$WEB.new" "$WEB"; rm -rf "$WEB.old" "$SITE_TMP"
if [ $SKIP_PHRASES = 0 ]; then
  /opt/svaram/voice/venv/bin/python "$SRC/tools/make_phrases.py" --out "$WEB" $(for c in ${LANGS//,/ }; do echo --lang "$c"; done) | tail -1
fi
chown -R root:root "$WEB"; chmod -R go=rX "$WEB"

if [ -n "$DOMAIN" ]; then
  mkdir -p /etc/nginx/svaram
  install -m 644 "$SRC/deploy/nginx.api-proxy.conf" /etc/nginx/svaram/api-proxy.conf
  sed "s/svaram\.live/$DOMAIN/g" "$SRC/deploy/nginx.sample.conf" > /etc/nginx/sites-available/$DOMAIN
  say "   nginx site written to /etc/nginx/sites-available/$DOMAIN"
  say "   next: get a certificate (e.g. certbot certonly --webroot -w $WEB -d $DOMAIN), link the site into sites-enabled, nginx -t, reload"
fi

# ------------------------------------------------------------------ 9. self-test
say "9/9 self-test"
env PYTHONUNBUFFERED=1 /opt/svaram/voice/venv/bin/python "$SRC/tools/selftest.py" $(for c in ${LANGS//,/ }; do echo --lang "$c"; done)
say "DONE. Svaram answers on http://127.0.0.1:8200; pages in $WEB"
