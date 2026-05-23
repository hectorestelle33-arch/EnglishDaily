from __future__ import annotations

import re
from email.utils import parsedate_to_datetime
from html import unescape

import feedparser
import requests

from .models import RawArticle
from .sources import CHINA_DEEP_READ_SOURCES, RSS_SOURCES, NewsSource


TOO_SHORT_SUMMARY_CHARS = 45
DEFAULT_PER_SOURCE_LIMIT = 10
SOURCE_CATEGORY_LIMIT = 4
SOURCE_TOTAL_LIMIT = 8
CATEGORY_CANDIDATE_LIMITS = {
    "World News": 18,
    "Technology & AI": 12,
    "Business & Economy": 10,
    "Society & Culture": 10,
    "Feature / Long Read": 8,
    "English Learning": 8,
}
LOW_VALUE_KEYWORDS = {
    "sport",
    "sports",
    "football",
    "soccer",
    "basketball",
    "tennis",
    "cricket",
    "celebrity",
    "celebrities",
    "gossip",
    "red carpet",
    "box office",
    "stock jumps",
    "stock falls",
    "shares jump",
    "shares fall",
}
CHINA_PRIORITY_KEYWORDS = {
    "就业",
    "失业",
    "工资",
    "收入",
    "房价",
    "楼市",
    "债务",
    "医保",
    "养老",
    "教育",
    "事故",
    "调查",
    "处罚",
    "通报",
    "维权",
    "欠薪",
    "消费",
    "裁员",
    "人口",
    "生育",
    "食品安全",
    "医疗",
    "住房",
    "房地产",
    "地方债",
}
CHINA_PROPAGANDA_KEYWORDS = {
    "成就",
    "捷报",
    "高质量发展",
    "中国力量",
    "中国速度",
    "世界领先",
    "再创新高",
    "彰显",
    "谱写新篇章",
    "重大突破",
    "喜报",
    "走在前列",
}


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


def fetch_candidates(
    timeout: int = 20,
    per_source_limit: int = DEFAULT_PER_SOURCE_LIMIT,
    max_candidates: int = 50,
    recent_articles: list[RawArticle] | None = None,
) -> tuple[list[RawArticle], list[str]]:
    articles: list[RawArticle] = []
    errors: list[str] = []

    for source in RSS_SOURCES:
        try:
            articles.extend(fetch_source(source, timeout=timeout, limit=per_source_limit))
        except Exception as exc:  # RSS availability changes; one source should not break the briefing.
            errors.append(f"{source.name}: {exc}")

    recent_articles = recent_articles or []
    candidates = deduplicate_articles(articles)
    candidates = filter_recent_duplicates(candidates, recent_articles)
    candidates = filter_low_value_candidates(candidates)
    candidates = balance_candidates(candidates, max_candidates=max_candidates)
    return candidates, errors


def fetch_china_candidates(
    timeout: int = 20,
    per_source_limit: int = 20,
    max_candidates: int = 80,
    recent_articles: list[RawArticle] | None = None,
) -> tuple[list[RawArticle], list[str]]:
    articles: list[RawArticle] = []
    errors: list[str] = []

    for source in CHINA_DEEP_READ_SOURCES:
        try:
            articles.extend(fetch_source(source, timeout=timeout, limit=per_source_limit))
        except Exception as exc:
            errors.append(f"{source.name}: {exc}")

    recent_articles = recent_articles or []
    candidates = deduplicate_articles(articles)
    candidates = filter_recent_duplicates(candidates, recent_articles)
    candidates = sorted(candidates, key=china_candidate_score, reverse=True)
    return candidates[:max_candidates], errors


def fetch_china_candidates_with_meta(
    timeout: int = 20,
    per_source_limit: int = 20,
    max_candidates: int = 80,
    ai_candidates: int = 30,
    recent_articles: list[RawArticle] | None = None,
) -> tuple[list[RawArticle], dict[str, int], list[str]]:
    articles: list[RawArticle] = []
    errors: list[str] = []

    for source in CHINA_DEEP_READ_SOURCES:
        try:
            articles.extend(fetch_source(source, timeout=timeout, limit=per_source_limit))
        except Exception as exc:
            errors.append(f"{source.name}: {exc}")

    recent_articles = recent_articles or []
    deduped = deduplicate_articles(articles)
    recent_filtered = filter_recent_duplicates(deduped, recent_articles)
    ranked = sorted(recent_filtered, key=china_candidate_score, reverse=True)
    candidate_pool = ranked[:max_candidates]
    selected_for_ai = candidate_pool[:ai_candidates]
    meta = {
        "raw_fetched_count": len(articles),
        "deduped_count": len(deduped),
        "after_recent_dedupe_count": len(recent_filtered),
        "candidate_pool_count": len(candidate_pool),
        "sent_to_ai_count": len(selected_for_ai),
    }
    return selected_for_ai, meta, errors


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


def filter_recent_duplicates(articles: list[RawArticle], recent_articles: list[RawArticle]) -> list[RawArticle]:
    recent_links = {article.link for article in recent_articles if article.link}
    recent_keys = {normalize_title(article.title) for article in recent_articles if article.title}
    recent_signatures = {article_signature(article) for article in recent_articles if article.original_summary}

    filtered: list[RawArticle] = []
    for article in articles:
        if article.link in recent_links:
            continue
        if normalize_title(article.title) in recent_keys:
            continue
        if article_signature(article) in recent_signatures:
            continue
        filtered.append(article)
    return filtered


def filter_low_value_candidates(articles: list[RawArticle]) -> list[RawArticle]:
    filtered: list[RawArticle] = []
    for article in articles:
        text = f"{article.title} {article.original_summary}".lower()
        if len(article.original_summary) < TOO_SHORT_SUMMARY_CHARS:
            continue
        if any(keyword in text for keyword in LOW_VALUE_KEYWORDS):
            continue
        filtered.append(article)
    return filtered


def balance_candidates(articles: list[RawArticle], max_candidates: int) -> list[RawArticle]:
    source_category_counts: dict[tuple[str, str], int] = {}
    source_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    buckets: dict[str, list[RawArticle]] = {category: [] for category in CATEGORY_CANDIDATE_LIMITS}
    overflow: list[RawArticle] = []

    for article in articles:
        category_limit = CATEGORY_CANDIDATE_LIMITS.get(article.category, 8)
        source_key = (article.source, article.category)
        if category_counts.get(article.category, 0) >= category_limit:
            overflow.append(article)
            continue
        if source_category_counts.get(source_key, 0) >= SOURCE_CATEGORY_LIMIT:
            overflow.append(article)
            continue
        if source_counts.get(article.source, 0) >= SOURCE_TOTAL_LIMIT:
            overflow.append(article)
            continue
        buckets.setdefault(article.category, []).append(article)
        category_counts[article.category] = category_counts.get(article.category, 0) + 1
        source_category_counts[source_key] = source_category_counts.get(source_key, 0) + 1
        source_counts[article.source] = source_counts.get(article.source, 0) + 1

    selected: list[RawArticle] = []
    category_order = list(CATEGORY_CANDIDATE_LIMITS.keys())
    while len(selected) < max_candidates:
        added = False
        for category in category_order:
            bucket = buckets.get(category, [])
            if bucket:
                selected.append(bucket.pop(0))
                added = True
                if len(selected) >= max_candidates:
                    break
        if not added:
            break

    for article in overflow:
        if len(selected) >= max_candidates:
            break
        if article not in selected:
            selected.append(article)

    return selected[:max_candidates]


def normalize_title(title: str) -> str:
    text = re.sub(r"\s+", "", title.lower())
    if re.search(r"[\u4e00-\u9fff]", text):
        return re.sub(r"[^\u4e00-\u9fffa-z0-9]", "", text)[:40]
    words = re.findall(r"[a-z0-9]+", title.lower())
    return " ".join(words[:14])


def article_signature(article: RawArticle) -> str:
    text = f"{article.title} {article.original_summary}".lower()
    if re.search(r"[\u4e00-\u9fff]", text):
        return re.sub(r"[^\u4e00-\u9fffa-z0-9]", "", text)[:80]
    words = [word for word in re.findall(r"[a-z0-9]+", text) if len(word) > 3]
    return " ".join(words[:24])


def china_candidate_score(article: RawArticle) -> int:
    text = f"{article.title} {article.original_summary}"
    score = 0
    score += sum(3 for keyword in CHINA_PRIORITY_KEYWORDS if keyword in text)
    score -= sum(4 for keyword in CHINA_PROPAGANDA_KEYWORDS if keyword in text)
    if len(article.original_summary) >= 80:
        score += 2
    if article.source.startswith("Google新闻"):
        score += 1
    return score
