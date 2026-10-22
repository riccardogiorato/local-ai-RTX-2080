#!/usr/bin/env bash
# One harness run through the recording proxy. Usage: run-one.sh <pi|opencode|grok|claude> <tag> <port> <workdir> <prompt-file>
# The proxy must already be listening on 127.0.0.1:8081. Labels the proxy rows with <tag>,
# runs the harness headless in <workdir> with a 600 s cap, saves the transcript next to it.
set -u
TAG="$1"; WORK="$2"; PROMPT_FILE="$3"; PORT="${4:-8081}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PROXY="http://127.0.0.1:$PORT"
# curl label FIRST so every row of this run is tagged
curl -s "$PROXY/_label" -H 'Content-Type: application/json' -d "{\"harness\":\"$TAG\"}" >/dev/null
PROMPT="$(cat "$PROMPT_FILE")"
WORK="$(readlink -f "$WORK")"
OUT="$WORK/../transcript-$TAG.out"
ERR="$WORK/../transcript-$TAG.err"

PI_BIN="$HOME/.local/share/mise/installs/pi/latest/pi/pi"
[ -x "$PI_BIN" ] || PI_BIN=pi

case "$TAG" in
  pi-*)
    ( cd "$WORK" && PI_OFFLINE=1 timeout 900 "$PI_BIN" --provider strata-proxy \
        --model local-model --mode json --no-session -p "$PROMPT" < /dev/null ) > "$OUT" 2> "$ERR"
    ;;
  opencode-*)
    ( cd "$WORK" && timeout 900 opencode run --standalone -m strata-proxy/local-model \
        --auto --format json "$PROMPT" < /dev/null ) > "$OUT" 2> "$ERR"
    ;;
  grok-*)
    ( cd "$WORK" && timeout 900 grok -m local-model --always-approve \
        --disable-web-search --max-turns "${GROK_MAX_TURNS:-24}" --cwd "$WORK" -p "$PROMPT" < /dev/null ) > "$OUT" 2> "$ERR"
    ;;
  claude-*)
    mkdir -p "$WORK/../claude-config"
    ( cd "$WORK" && timeout 900 env \
        CLAUDE_CONFIG_DIR="$WORK/../claude-config" \
        ANTHROPIC_BASE_URL="$PROXY" \
        ANTHROPIC_API_KEY=local \
        ANTHROPIC_AUTH_TOKEN=local \
        ANTHROPIC_MODEL=local-model \
        ANTHROPIC_SMALL_FAST_MODEL=local-model \
        ANTHROPIC_DEFAULT_HAIKU_MODEL=local-model \
        ANTHROPIC_DEFAULT_SONNET_MODEL=local-model \
        ANTHROPIC_DEFAULT_OPUS_MODEL=local-model \
        CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 \
        DISABLE_TELEMETRY=1 \
        claude -p "$PROMPT" --model local-model --dangerously-skip-permissions \
        --max-turns "${CLAUDE_MAX_TURNS:-24}" --output-format json < /dev/null ) > "$OUT" 2> "$ERR"
    ;;
  codex-*)
    # lean scratch CODEX_HOME (no desktop plugins/MCP): responses wire via the proxy;
    # direct binary path - the mise shim stalls like pi's did (AG-Bench PI_BIN precedent)
    CODEX_BIN="$HOME/.local/share/mise/installs/codex/0.163.0/bin/codex"
    [ -x "$CODEX_BIN" ] || CODEX_BIN=codex
    CODEX_HOME_DIR="${CODEX_HOME_DIR:-/home/riccardogiorato/Desktop/github/local-ai-rtx2080/experiments/strata-codex-agbench-20261022/codex-home}"
    ( cd "$WORK" && CODEX_HOME="$CODEX_HOME_DIR" STRATA_API_KEY=local \
        timeout 900 "$CODEX_BIN" exec --skip-git-repo-check "$PROMPT" < /dev/null ) > "$OUT" 2> "$ERR"
    ;;
  *) echo "unknown tag $TAG" >&2; exit 2 ;;
esac
RC=$?
echo "{\"tag\":\"$TAG\",\"rc\":$RC,\"wall_hint\":\"see proxy.jsonl\"}"
exit $RC
