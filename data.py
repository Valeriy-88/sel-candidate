import json
from pathlib import Path
from typing import Any, List


array_text = []
quiz_data = []
NICKS_FILE = Path("nicks.json")


def load_nicks() -> Any:
    """Загружает список ников из файла"""
    try:
        with open(NICKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_nicks(nicks: List[str]) -> None:
    """Сохраняет список ников в файл"""
    with open(NICKS_FILE, "w", encoding="utf-8") as f:
        json.dump(nicks, f, ensure_ascii=False, indent=2)


nicknames = load_nicks()
