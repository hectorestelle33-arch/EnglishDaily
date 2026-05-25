from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .config import DATA_DIR, ensure_dirs
from .dates import app_today_iso, parse_app_date, recent_allowed_dates
from .models import AnalyzedArticle, ChinaDeepRead


def save_briefing(
    articles: list[AnalyzedArticle],
    deep_read: AnalyzedArticle | None,
    deep_read_mode: str = "World",
    china_deep_read: ChinaDeepRead | None = None,
) -> Path:
    ensure_dirs()
    today = app_today_iso()
    articles = filter_articles_for_briefing_date(articles, today)
    if deep_read and not article_matches_briefing_date(deep_read, today):
        deep_read = None
    path = DATA_DIR / f"briefing-{today}.json"
    payload = {
        "date": today,
        "articles": [asdict(article) for article in articles],
        "deep_read": asdict(deep_read) if deep_read else None,
        "deep_read_mode": deep_read_mode,
        "china_deep_read": asdict(china_deep_read) if china_deep_read else None,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    cleanup_old_briefings(keep=5)
    return path


def load_today_briefing() -> tuple[list[AnalyzedArticle], AnalyzedArticle | None, str, ChinaDeepRead | None] | None:
    ensure_dirs()
    path = DATA_DIR / f"briefing-{app_today_iso()}.json"
    return load_briefing_file(path)


def load_latest_briefing() -> tuple[list[AnalyzedArticle], AnalyzedArticle | None, str, ChinaDeepRead | None] | None:
    files = list_saved_briefings()
    if not files:
        return None
    return load_briefing_file(files[0])


def load_briefing_file(path: Path) -> tuple[list[AnalyzedArticle], AnalyzedArticle | None, str, ChinaDeepRead | None] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    briefing_date = str(payload.get("date") or path.stem.replace("briefing-", ""))
    articles = [article_from_dict(item) for item in payload.get("articles", [])]
    articles = filter_articles_for_briefing_date(articles, briefing_date)
    deep_read_payload = payload.get("deep_read")
    deep_read = article_from_dict(deep_read_payload) if deep_read_payload else None
    if deep_read and not article_matches_briefing_date(deep_read, briefing_date):
        deep_read = None
    china_payload = payload.get("china_deep_read")
    china_deep_read = china_deep_read_from_dict(china_payload) if china_payload else None
    return articles, deep_read, str(payload.get("deep_read_mode") or "World"), china_deep_read


def article_matches_briefing_date(article: AnalyzedArticle, briefing_date: str, days: int = 3) -> bool:
    base_date = parse_app_date(briefing_date)
    published_date = parse_app_date(article.published_time)
    if not base_date or not published_date:
        return False
    return published_date in recent_allowed_dates(base_date=base_date, days=days)


def filter_articles_for_briefing_date(
    articles: list[AnalyzedArticle], briefing_date: str, days: int = 3
) -> list[AnalyzedArticle]:
    return [article for article in articles if article_matches_briefing_date(article, briefing_date, days=days)]


def article_from_dict(data: dict) -> AnalyzedArticle:
    valid_keys = AnalyzedArticle.__dataclass_fields__.keys()
    cleaned = {key: value for key, value in data.items() if key in valid_keys}
    return AnalyzedArticle(**cleaned)


def china_deep_read_from_dict(data: dict) -> ChinaDeepRead:
    valid_keys = ChinaDeepRead.__dataclass_fields__.keys()
    cleaned = {key: value for key, value in data.items() if key in valid_keys}
    return ChinaDeepRead(**cleaned)


def list_saved_briefings(keep: int = 5) -> list[Path]:
    ensure_dirs()
    files = sorted(DATA_DIR.glob("briefing-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    return files[:keep]


def cleanup_old_briefings(keep: int = 5) -> None:
    for path in sorted(DATA_DIR.glob("briefing-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)[keep:]:
        path.unlink(missing_ok=True)


def build_feedback_note() -> str:
    marks = load_user_marks()
    if not marks:
        return "No prior difficulty feedback yet."

    recent_articles: dict[str, AnalyzedArticle] = {}
    for path in list_saved_briefings(keep=5):
        loaded = load_briefing_file(path)
        if not loaded:
            continue
        articles, deep_read, _, _ = loaded
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
    for path in list_saved_briefings(keep=5):
        loaded = load_briefing_file(path)
        if not loaded:
            continue
        articles, deep_read, _, _ = loaded
        for article in articles + ([deep_read] if deep_read else []):
            if article.link in saved_links:
                articles_by_link[article.link] = article

    return list(articles_by_link.values())


def load_recent_articles(keep: int = 2) -> list[AnalyzedArticle]:
    recent: dict[str, AnalyzedArticle] = {}
    for path in list_saved_briefings(keep=keep):
        loaded = load_briefing_file(path)
        if not loaded:
            continue
        articles, deep_read, _, _ = loaded
        for article in articles + ([deep_read] if deep_read else []):
            recent[article.link] = article
    return list(recent.values())


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
