#!/usr/bin/env bash
set -euo pipefail
TIMESTEPS="${1:-200000}"
CONFIG="${2:-config/config.yaml}"
python -m src.rl.train --config "$CONFIG" --timesteps "$TIMESTEPS"
