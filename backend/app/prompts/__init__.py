"""Versioned prompt loader. Prompts are plain text files in this package."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_DIR = Path(__file__).parent

PROMPT_VERSIONS = {
    "answer": "answer_v1",
    "claim_extraction": "claim_extraction_v1",
    "explanation": "explanation_v1",
}


@lru_cache
def load_prompt(name: str) -> str:
    path = _DIR / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"prompt not found: {name}")
    return path.read_text(encoding="utf-8").strip()
