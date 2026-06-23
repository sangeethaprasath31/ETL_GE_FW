from __future__ import annotations

import json
from pathlib import Path

def read_config(config_path: str | Path) -> dict:
    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)
