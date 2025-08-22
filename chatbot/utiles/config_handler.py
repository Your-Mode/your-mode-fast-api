from typing import Any

import yaml


def load_config(path: str) -> dict[str, Any]:
    config = {}
    with open(path, encoding="utf-8") as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config
