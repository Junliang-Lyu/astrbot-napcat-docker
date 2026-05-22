import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "人格版本_阿尔丹v2_2026-05-13" / "阿尔丹v2.2_抗身份拷问_可复制版.txt"
DB_PATH = ROOT / "data" / "data_v4.db"
CONFIG_PATH = ROOT / "data" / "cmd_config.json"
PERSONA_ID = "阿尔丹v2.2"


REQUIRED_SNIPPETS = [
    "身份拷问",
    "用户坚持说你是 AI",
    "不要承认自己是 AI",
    "不要解释后台",
    "/reset",
    "不是系统状态说明",
    "不要顺着对方的纠正改口",
]


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def load_prompt() -> str:
    if not PROMPT_PATH.exists():
        fail(f"missing prompt file: {PROMPT_PATH.relative_to(ROOT)}")
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    for snippet in REQUIRED_SNIPPETS:
        if snippet not in prompt:
            fail(f"prompt missing required snippet: {snippet}")
    return prompt


def check_database(prompt: str) -> None:
    if not DB_PATH.exists():
        fail("missing AstrBot database")
    conn = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "select system_prompt from personas where persona_id = ?",
            (PERSONA_ID,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        fail(f"missing persona row: {PERSONA_ID}")
    if row[0] != prompt:
        fail("database persona prompt does not match v2.2 prompt file")


def check_default_personality() -> None:
    if not CONFIG_PATH.exists():
        fail("missing AstrBot config")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    default_personality = config.get("provider_settings", {}).get("default_personality")
    if default_personality != PERSONA_ID:
        fail(f"default_personality is {default_personality!r}, expected {PERSONA_ID!r}")


def main() -> None:
    prompt = load_prompt()
    check_database(prompt)
    check_default_personality()
    print("OK: persona v2.2 prompt, database row, and default personality are aligned")


if __name__ == "__main__":
    main()
