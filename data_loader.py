import csv
import json
from pathlib import Path

from question_bank import QUESTION_BANK


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_PATH = DATA_DIR / "user_question_bank.csv"
JSON_PATH = DATA_DIR / "user_question_bank.json"


def _normalize_question(raw: dict, idx: int) -> dict:
    choices = raw.get("choices")
    if not choices:
        choices = [
            raw.get("choice1", ""),
            raw.get("choice2", ""),
            raw.get("choice3", ""),
            raw.get("choice4", ""),
        ]

    if len(choices) != 4:
        raise ValueError(f"問題{idx}: choicesは4つ必要です。")

    answer = raw.get("answer")
    if isinstance(answer, str) and answer.isdigit():
        answer = int(answer)
    if not isinstance(answer, int):
        raise ValueError(f"問題{idx}: answerは整数(0-3)で指定してください。")
    if answer < 0 or answer > 3:
        raise ValueError(f"問題{idx}: answerは0-3で指定してください。")

    return {
        "id": str(raw.get("id") or f"U{idx:04d}"),
        "field": str(raw.get("field") or "未分類"),
        "year": str(raw.get("year") or "不明"),
        "difficulty": int(raw.get("difficulty") or 2),
        "question": str(raw.get("question") or "").strip(),
        "choices": [str(c).strip() for c in choices],
        "answer": answer,
        "explanation": str(raw.get("explanation") or "").strip(),
    }


def _load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("JSONのルートは配列である必要があります。")
    return [_normalize_question(item, i + 1) for i, item in enumerate(data)]


def _load_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        raise ValueError("CSVにデータ行がありません。")
    return [_normalize_question(row, i + 1) for i, row in enumerate(rows)]


def load_question_bank() -> tuple[list[dict], str]:
    """
    戻り値:
      questions: 問題リスト
      source: "default" | "json" | "csv"
    """
    if JSON_PATH.exists():
        return _load_json(JSON_PATH), "json"
    if CSV_PATH.exists():
        return _load_csv(CSV_PATH), "csv"
    return QUESTION_BANK, "default"
