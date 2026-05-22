from __future__ import annotations

from collections import defaultdict

from .ai import analyze_article
from .config import Settings
from .fetcher import fetch_candidates
from .models import AnalyzedArticle


DAILY_QUOTAS = {
    "World News": 2,
    "Technology & AI": 2,
    "Society & Culture": 2,
    "Business & Economy": 1,
}


FEATURE_CATEGORIES = {"Feature / Long Read", "English Learning"}


def generate_briefing(
    target_level: str, settings: Settings, feedback_note: str = ""
) -> tuple[list[AnalyzedArticle], AnalyzedArticle | None, list[str]]:
    raw_articles, errors = fetch_candidates(timeout=settings.request_timeout, max_candidates=settings.max_candidates)
    analyzed: list[AnalyzedArticle] = []

    for article in raw_articles:
        try:
            analyzed.append(analyze_article(article, target_level, settings, feedback_note=feedback_note))
        except Exception as exc:
            errors.append(f"{article.source} - {article.title}: {exc}")

    selected = select_daily_top(analyzed)
    deep_read = select_deep_read(selected, analyzed)
    if deep_read:
        deep_read.deep_read = True
    return selected, deep_read, errors


def article_rank(article: AnalyzedArticle) -> tuple[int, int]:
    return (article.importance_score + article.reading_value_score, article.reading_value_score)


def select_daily_top(articles: list[AnalyzedArticle]) -> list[AnalyzedArticle]:
    eligible = [article for article in articles if not article.filter_out]
    by_category: dict[str, list[AnalyzedArticle]] = defaultdict(list)
    for article in sorted(eligible, key=article_rank, reverse=True):
        by_category[article.category].append(article)

    selected: list[AnalyzedArticle] = []
    used_links: set[str] = set()

    for category, quota in DAILY_QUOTAS.items():
        for article in by_category.get(category, [])[:quota]:
            selected.append(article)
            used_links.add(article.link)

    feature_pool = [
        article
        for article in sorted(eligible, key=article_rank, reverse=True)
        if article.category in FEATURE_CATEGORIES and article.link not in used_links
    ]
    if feature_pool:
        selected.append(feature_pool[0])
        used_links.add(feature_pool[0].link)

    if len(selected) < 8:
        for article in sorted(eligible, key=article_rank, reverse=True):
            if article.link in used_links:
                continue
            selected.append(article)
            used_links.add(article.link)
            if len(selected) >= 8:
                break

    return selected[:8]


def select_deep_read(selected: list[AnalyzedArticle], all_articles: list[AnalyzedArticle]) -> AnalyzedArticle | None:
    pool = selected or [article for article in all_articles if not article.filter_out]
    if not pool:
        return None
    return sorted(pool, key=lambda item: (item.reading_value_score, item.importance_score), reverse=True)[0]
