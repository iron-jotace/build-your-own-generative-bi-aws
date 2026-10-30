\
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_settings(path="config/settings.json"):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path

    if not path.exists():
        example = ROOT / "config/settings.example.json"
        raise FileNotFoundError(
            f"Missing {path}. Copy {example} to {path} and configure your AWS values."
        )

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
