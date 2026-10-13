#!/usr/bin/env bash
# HDD rotation 2026-10-14, owner-approved queue.
# Stage 1: flashnext-gsq-rco + flashnext-coder -> archive copy ONLY (stay on SSD: fleet rows).
# Stage 2: saluki-27b, d1-3B, d1-3B-gguf, atomicchat-d1, laya-gguf -> copy, verify sha256, then delete on SSD.
set -u
LOG=/home/riccardogiorato/models/hdd-rotation-20261014/rotate.log
DEST=/mnt/archive/local-models
M=/home/riccardogiorato/models
log(){ echo "[$(date -Is)] $*" | tee -a "$LOG"; }
verify_and_report(){
  local src="$1" dst="$2" name="$3"
  local sd dd sums_s sums_d
  sd=$(mktemp) ; dd=$(mktemp)
  (cd "$M/$src" && find . -type f ! -name .rw-test -exec sha256sum {} + | sort) > "$sd"
  (cd "$dst/$src" && find . -type f ! -name .rw-test -exec sha256sum {} + | sort) > "$dd"
  if diff -q "$sd" "$dd" >/dev/null; then
    log "VERIFY PASS $name ($(wc -l < "$sd") files, sha256-identical)"
    rm -f "$sd" "$dd"; return 0
  else
    log "VERIFY FAIL $name"; diff "$sd" "$dd" | head -20 | tee -a "$LOG"; rm -f "$sd" "$dd"; return 1
  fi
}
log "=== rotation start ==="
log "stage 1: backup flashnext pair (rsync -rtH, hardlink dedup expected on dest)"
rsync -rtH --info=progress2 "$M/flashnext-gsq-rco" "$M/flashnext-coder" "$DEST" || exit 1
log "stage 1 copy done"
for d in flashnext-gsq-rco flashnext-coder; do verify_and_report "$d" "$DEST" "archive-copy/$d" || exit 3; done
log "stage 1 VERIFIED: fleet-record pair now backed up on HDD"
log "stage 2: rotation copy"
rsync -rtH --info=progress2 "$M/saluki-27b" "$M/d1-3B" "$M/d1-3B-gguf" "$M/atomicchat-d1" "$M/laya-gguf" "$DEST" || exit 1
for d in saluki-27b d1-3B d1-3B-gguf atomicchat-d1 laya-gguf; do verify_and_report "$d" "$DEST" "rotate/$d" || exit 3; done
log "stage 2 VERIFIED, deleting SSD source dirs"
for d in saluki-27b d1-3B d1-3B-gguf atomicchat-d1 laya-gguf; do rm -rf "$M/$d" && log "deleted $M/$d"; done
log "=== rotation complete ==="
df -h /home /mnt/archive | tee -a "$LOG"
