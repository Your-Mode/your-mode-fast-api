import json
from typing import Any

import yaml


def load_yaml(path: str) -> dict[str, Any]:
    config = {}
    with open(path, encoding="utf-8") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config


def load_json(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        return json.load(file)
