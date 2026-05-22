from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
EXPORT_DIR = ROOT_DIR / "exports"


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_thinking: str = "disabled"
    guardian_api_key: str = ""
    max_candidates: int = 32
    request_timeout: int = 90


def load_settings() -> Settings:
    load_dotenv(ROOT_DIR / ".env")
    return Settings(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "").strip(),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip() or "deepseek-v4-flash",
        deepseek_thinking=os.getenv("DEEPSEEK_THINKING", "disabled").strip().lower() or "disabled",
        guardian_api_key=os.getenv("GUARDIAN_API_KEY", "").strip(),
        request_timeout=int(os.getenv("DEEPSEEK_TIMEOUT", "90")),
    )


def ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    EXPORT_DIR.mkdir(exist_ok=True)
