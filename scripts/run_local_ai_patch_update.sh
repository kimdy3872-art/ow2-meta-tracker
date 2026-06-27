#!/bin/zsh

set -u

PROJECT_DIR="/Users/dykim/Documents/DAProj/(Clone) DA_Overwatch analysis"
STATE_DIR="$PROJECT_DIR/data/local_run_state"
LOG_DIR="$PROJECT_DIR/logs"
LAST_SUCCESS_FILE="$STATE_DIR/patch_ai_last_success.txt"
LOCK_DIR="$STATE_DIR/patch_ai_update.lock"

MIN_HOUR="${MIN_HOUR:-9}"
OLLAMA_MODEL="${OLLAMA_MODEL:-qwen3:14b}"
OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-180}"
OLLAMA_GENERATE_URL="${OLLAMA_GENERATE_URL:-http://localhost:11434/api/generate}"
OLLAMA_TAGS_URL="${OLLAMA_TAGS_URL:-http://localhost:11434/api/tags}"

mkdir -p "$STATE_DIR" "$LOG_DIR"

LOG_FILE="$LOG_DIR/local_ai_patch_update.log"
TODAY="$(/bin/date +%F)"
NOW_HOUR="$(/bin/date +%H)"
NOW_MINUTE="$(/bin/date +%M)"

log() {
  /bin/echo "[$(/bin/date '+%F %T')] $*" | /usr/bin/tee -a "$LOG_FILE"
}

has_today_ai_analysis() {
  /usr/bin/python3 - <<'PY'
import json
from datetime import date
from pathlib import Path

path = Path("data/patch_notes/patch_ai_analysis.json")
today = date.today().isoformat()
if not path.exists():
    raise SystemExit(1)

try:
    rows = json.loads(path.read_text(encoding="utf-8"))
except json.JSONDecodeError:
    raise SystemExit(1)

if any(str(row.get("analysis_date")) == today for row in rows if isinstance(row, dict)):
    raise SystemExit(0)
raise SystemExit(1)
PY
}

if (( 10#$NOW_HOUR < MIN_HOUR )); then
  log "skip: current time ${NOW_HOUR}:${NOW_MINUTE} is before ${MIN_HOUR}:00"
  exit 0
fi

if [[ -f "$LAST_SUCCESS_FILE" ]] && [[ "$(/bin/cat "$LAST_SUCCESS_FILE")" == "$TODAY" ]]; then
  if has_today_ai_analysis; then
    log "skip: patch AI analysis already succeeded today ($TODAY)"
    exit 0
  fi
  log "warn: success marker exists but today's AI analysis is missing; running again"
fi

if ! /bin/mkdir "$LOCK_DIR" 2>/dev/null; then
  log "skip: another patch AI update is already running"
  exit 0
fi
trap '/bin/rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

cd "$PROJECT_DIR" || {
  log "error: cannot enter project dir: $PROJECT_DIR"
  exit 1
}

BRANCH="$(/usr/bin/git branch --show-current 2>/dev/null)"
if [[ -z "$BRANCH" ]]; then
  log "error: cannot detect current git branch"
  exit 1
fi

NON_PATCH_DIRTY="$(
  {
    /usr/bin/git diff --name-only
    /usr/bin/git diff --cached --name-only
    /usr/bin/git ls-files --others --exclude-standard
  } | /usr/bin/grep -v '^data/patch_notes/' | /usr/bin/grep -v '^data/local_run_state/' | /usr/bin/grep -v '^logs/' || true
)"

if [[ -z "$NON_PATCH_DIRTY" ]]; then
  log "sync: pulling latest origin/$BRANCH"
  if ! /usr/bin/git pull --rebase origin "$BRANCH" >>"$LOG_FILE" 2>&1; then
    log "error: git pull --rebase failed"
    exit 1
  fi
else
  log "warn: local non-patch changes exist, skipping git pull"
  log "$NON_PATCH_DIRTY"
fi

if ! /usr/bin/curl -sS --max-time 5 "$OLLAMA_TAGS_URL" | /usr/bin/grep -q "\"$OLLAMA_MODEL\""; then
  log "error: Ollama model is not reachable: $OLLAMA_MODEL"
  exit 1
fi

log "run: generating patch AI analysis with $OLLAMA_MODEL"
if ! ENABLE_OLLAMA_ANALYSIS=1 \
  OLLAMA_MODEL="$OLLAMA_MODEL" \
  OLLAMA_TIMEOUT="$OLLAMA_TIMEOUT" \
  OLLAMA_GENERATE_URL="$OLLAMA_GENERATE_URL" \
  /usr/bin/python3 update.py --mode patch >>"$LOG_FILE" 2>&1; then
  log "error: update.py --mode patch failed"
  exit 1
fi

if ! has_today_ai_analysis; then
  log "error: today's AI analysis was not created"
  exit 1
fi

/usr/bin/git add data/patch_notes/patch_notes.json data/patch_notes/patch_ai_analysis.json 2>/dev/null

if /usr/bin/git diff --cached --quiet -- data/patch_notes; then
  log "ok: today's AI analysis already matches git state"
  /bin/echo "$TODAY" > "$LAST_SUCCESS_FILE"
  exit 0
fi

COMMIT_MESSAGE="chore: update patch AI analysis - $TODAY"
log "commit: $COMMIT_MESSAGE"
if ! /usr/bin/git commit -m "$COMMIT_MESSAGE" >>"$LOG_FILE" 2>&1; then
  log "error: git commit failed"
  exit 1
fi

log "push: origin $BRANCH"
if ! /usr/bin/git push origin "$BRANCH" >>"$LOG_FILE" 2>&1; then
  log "error: git push failed"
  exit 1
fi

/bin/echo "$TODAY" > "$LAST_SUCCESS_FILE"
log "done: local patch AI analysis updated and pushed"
