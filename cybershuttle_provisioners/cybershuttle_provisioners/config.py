from os.path import dirname
from pathlib import Path

TEMPLATE_DIR = Path(dirname(__file__)) / "templates"


def jsonify(data: dict) -> str:
    import json

    data = {k: v.decode() if isinstance(v, bytes) else v for k, v in data.items()}
    return json.dumps(data, ensure_ascii=False)
