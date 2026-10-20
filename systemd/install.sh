#!/usr/bin/env bash
# One-time: link the repo-tracked serve stack into the live locations.
# Workflow after this: edit files here, commit, then `systemctl --user daemon-reload`
# (and `systemctl --user restart strata-serve` if engine args changed).
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ln -sf "$repo/systemd/strata-serve.service"        ~/.config/systemd/user/strata-serve.service
ln -sf "$repo/systemd/strata-power-limit-wait"     ~/.local/bin/strata-power-limit-wait
ln -sf "$repo/systemd/strata-mon"                  ~/.local/bin/strata-mon
systemctl --user daemon-reload
echo "linked. status:"; systemctl --user is-active strata-serve.service
