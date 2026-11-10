import os
import json
import sqlite3
from typing import Optional, Dict, Any


DB_NAME = "evaluations.db"
TABLE_SQL = """
CREATE TABLE IF NOT EXISTS attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    athlete TEXT NOT NULL,
    exercise TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    auto_valid INTEGER NOT NULL,
    auto_summary TEXT,           -- JSON: ipf_lights, percentage/score, level
    judge_valid INTEGER NOT NULL,
    judge_notes TEXT,
    angles TEXT                  -- JSON: knee, hip, torso, back (últimos ângulos)
);
"""


def _db_path(base_dir: Optional[str] = None) -> str:
    root = base_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    storage = os.path.join(root, "storage")
    os.makedirs(storage, exist_ok=True)
    return os.path.join(storage, DB_NAME)


def init_db(base_dir: Optional[str] = None) -> str:
    """Inicializa o banco SQLite e retorna o caminho do arquivo."""
    path = _db_path(base_dir)
    con = sqlite3.connect(path)
    try:
        con.execute(TABLE_SQL)
        con.commit()
    finally:
        con.close()
    return path


def save_attempt(record: Dict[str, Any], base_dir: Optional[str] = None) -> None:
    """Salva uma tentativa no banco.

    Campos esperados em `record`:
    - created_at: str (YYYY-MM-DD HH:MM:SS)
    - athlete: str
    - exercise: str
    - attempt: int
    - auto_valid: bool
    - auto_summary: dict (será serializado em JSON)
    - judge_valid: bool
    - judge_notes: str
    - angles: dict (será serializado em JSON)
    """
    path = _db_path(base_dir)
    con = sqlite3.connect(path)
    try:
        payload = (
            str(record.get("created_at")),
            str(record.get("athlete")),
            str(record.get("exercise")),
            int(record.get("attempt", 1)),
            int(1 if record.get("auto_valid") else 0),
            json.dumps(record.get("auto_summary") or {}, ensure_ascii=False),
            int(1 if record.get("judge_valid") else 0),
            str(record.get("judge_notes") or ""),
            json.dumps(record.get("angles") or {}, ensure_ascii=False),
        )
        con.execute(
            "INSERT INTO attempts (created_at, athlete, exercise, attempt, auto_valid, auto_summary, judge_valid, judge_notes, angles)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            payload,
        )
        con.commit()
    finally:
        con.close()


def fetch_attempts(base_dir: Optional[str] = None, limit: int = 200) -> list:
    """Busca tentativas salvas no banco, ordenadas da mais recente.

    Retorna lista de dicts com chaves:
    created_at, athlete, exercise, attempt, auto_valid, judge_valid, judge_notes
    """
    path = _db_path(base_dir)
    con = sqlite3.connect(path)
    try:
        cur = con.cursor()
        try:
            cur.execute(
                "SELECT created_at, athlete, exercise, attempt, auto_valid, judge_valid, judge_notes "
                "FROM attempts ORDER BY id DESC LIMIT ?",
                (int(limit),),
            )
        except Exception:
            return []
        rows = cur.fetchall() or []
        result = []
        for r in rows:
            try:
                result.append({
                    "created_at": str(r[0]),
                    "athlete": str(r[1]),
                    "exercise": str(r[2]),
                    "attempt": int(r[3]),
                    "auto_valid": bool(int(r[4]) == 1),
                    "judge_valid": bool(int(r[5]) == 1),
                    "judge_notes": str(r[6] or ""),
                })
            except Exception:
                continue
        return result
    finally:
        con.close()