from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .config import DATA_DIR, ensure_dirs
from .models import AnalyzedArticle


def save_briefing(articles: list[AnalyzedArticle], deep_read: AnalyzedArticle | None) -> Path:
    ensure_dirs()
    path = DATA_DIR / f"briefing-{date.today().isoformat()}.json"
    payload = {
        "date": date.today().isoformat(),
        "articles": [asdict(article) for article in articles],
        "deep_read": asdict(deep_read) if deep_read else None,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    cleanup_old_briefings(keep=2)
    return path


def load_today_briefing() -> tuple[list[AnalyzedArticle], AnalyzedArticle | None] | None:
    ensure_dirs()
    path = DATA_DIR / f"briefing-{date.today().isoformat()}.json"
    return load_briefing_file(path)


def load_latest_briefing() -> tuple[list[AnalyzedArticle], AnalyzedArticle | None] | None:
    files = list_saved_briefings()
    if not files:
        return None
    return load_briefing_file(files[0])


def load_briefing_file(path: Path) -> tuple[list[AnalyzedArticle], AnalyzedArticle | None] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    articles = [article_from_dict(item) for item in payload.get("articles", [])]
    deep_read_payload = payload.get("deep_read")
    deep_read = article_from_dict(deep_read_payload) if deep_read_payload else None
    return articles, deep_read


def article_from_dict(data: dict) -> AnalyzedArticle:
    valid_keys = AnalyzedArticle.__dataclass_fields__.keys()
    cleaned = {key: value for key, value in data.items() if key in valid_keys}
    return AnalyzedArticle(**cleaned)


def list_saved_briefings(keep: int = 2) -> list[Path]:
    ensure_dirs()
    files = sorted(DATA_DIR.glob("briefing-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    return files[:keep]


def cleanup_old_briefings(keep: int = 2) -> None:
    for path in sorted(DATA_DIR.glob("briefing-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[keep:]:
        path.unlink(missing_ok=True)


def build_feedback_note() -> str:
    marks = load_user_marks()
    if not marks:
        return "No prior difficulty feedback yet."

    recent_articles: dict[str, AnalyzedArticle] = {}
    for path in list_saved_briefings(keep=2):
        loaded = load_briefing_file(path)
        if not loaded:
            continue
        articles, deep_read = loaded
        for article in articles + ([deep_read] if deep_read else []):
            recent_articles[article.link] = article

    too_easy: list[str] = []
    too_hard: list[str] = []
    for link, item_marks in marks.items():
        article = recent_articles.get(link)
        label = f"{article.title} ({article.category}, {article.level})" if article else link
        if item_marks.get("too_easy"):
            too_easy.append(label)
        if item_marks.get("too_hard"):
            too_hard.append(label)

    parts = []
    if too_easy:
        parts.append("Previously marked too easy: " + "; ".join(too_easy[:5]))
    if too_hard:
        parts.append("Previously marked too hard: " + "; ".join(too_hard[:5]))
    if not parts:
        return "No prior difficulty feedback yet."
    return " | ".join(parts)


def load_saved_articles() -> list[AnalyzedArticle]:
    marks = load_user_marks()
    saved_links = {link for link, item_marks in marks.items() if item_marks.get("saved")}
    if not saved_links:
        return []

    articles_by_link: dict[str, AnalyzedArticle] = {}
    for path in list_saved_briefings(keep=2):
        loaded = load_briefing_file(path)
        if not loaded:
            continue
        articles, deep_read = loaded
        for article in articles + ([deep_read] if deep_read else []):
            if article.link in saved_links:
                articles_by_link[article.link] = article

    return list(articles_by_link.values())


def load_user_marks() -> dict[str, dict[str, bool]]:
    ensure_dirs()
    path = DATA_DIR / "user_marks.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_user_marks(marks: dict[str, dict[str, bool]]) -> None:
    ensure_dirs()
    path = DATA_DIR / "user_marks.json"
    path.write_text(json.dumps(marks, ensure_ascii=False, indent=2), encoding="utf-8")
