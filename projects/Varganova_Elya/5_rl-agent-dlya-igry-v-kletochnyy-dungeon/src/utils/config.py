from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(path: str | Path = "config/config.yaml") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    cfg.setdefault("env", {})
    cfg.setdefault("rewards", {})
    cfg.setdefault("training", {})
    cfg.setdefault("mlflow", {})
    cfg.setdefault("kafka", {})
    cfg.setdefault("inference", {})
    return cfg
