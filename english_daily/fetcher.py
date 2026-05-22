from __future__ import annotations

import re
from email.utils import parsedate_to_datetime
from html import unescape

import feedparser
import requests

from .models import RawArticle
from .sources import RSS_SOURCES, NewsSource


TOO_SHORT_SUMMARY_CHARS = 45


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_time(entry: object) -> str:
    published = getattr(entry, "published", "") or getattr(entry, "updated", "")
    if not published:
        return ""
    try:
        return parsedate_to_datetime(published).isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        return str(published)


def get_entry_summary(entry: object) -> str:
    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
    if not summary and getattr(entry, "content", None):
        summary = entry.content[0].get("value", "")
    return strip_html(summary)


def get_entry_text(entry: object, summary: str) -> str:
    content = ""
    if getattr(entry, "content", None):
        content = entry.content[0].get("value", "")
    elif getattr(entry, "summary", None):
        content = getattr(entry, "summary", "")

    text = strip_html(content)
    if len(text) <= len(summary) + 120:
        return ""
    return text


def fetch_source(source: NewsSource, timeout: int = 20, limit: int = 6) -> list[RawArticle]:
    headers = {"User-Agent": "EnglishDailyBriefing/0.1 (+local personal reader)"}
    response = requests.get(source.feed_url, headers=headers, timeout=timeout)
    response.raise_for_status()
    feed = feedparser.parse(response.content)

    articles: list[RawArticle] = []
    for entry in feed.entries[:limit]:
        title = strip_html(getattr(entry, "title", ""))
        link = getattr(entry, "link", "")
        summary = get_entry_summary(entry)
        article_text = get_entry_text(entry, summary)
        if not title or not link:
            continue
        articles.append(
            RawArticle(
                title=title,
                source=source.name,
                category=source.category,
                link=link,
                published_time=normalize_time(entry),
                original_summary=summary,
                article_text=article_text,
            )
        )
    return articles


def fetch_candidates(timeout: int = 20, per_source_limit: int = 5, max_candidates: int = 32) -> tuple[list[RawArticle], list[str]]:
    articles: list[RawArticle] = []
    errors: list[str] = []

    for source in RSS_SOURCES:
        try:
            articles.extend(fetch_source(source, timeout=timeout, limit=per_source_limit))
        except Exception as exc:  # RSS availability changes; one source should not break the briefing.
            errors.append(f"{source.name}: {exc}")

    return deduplicate_articles(articles)[:max_candidates], errors


def deduplicate_articles(articles: list[RawArticle]) -> list[RawArticle]:
    seen: set[str] = set()
    unique: list[RawArticle] = []

    for article in articles:
        key = normalize_title(article.title)
        if key in seen:
            continue
        seen.add(key)
        unique.append(article)
    return unique


def normalize_title(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", title.lower())
    return " ".join(words[:14])
