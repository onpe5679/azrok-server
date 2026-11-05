#!/usr/bin/env bash
set -euo pipefail

root="$HOME/32dev/azroksrv"
unit_dir="$HOME/.config/systemd/user"
mkdir -p "$unit_dir"
cp "$root"/deploy/u32ws/systemd/*.service "$unit_dir"/
systemctl --user daemon-reload
systemctl --user enable --now azrok-core.service azrok-bridge.service azrok-web.service
systemctl --user --no-pager --full status azrok-core.service azrok-bridge.service azrok-web.service

