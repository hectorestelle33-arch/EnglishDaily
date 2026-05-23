from __future__ import annotations

from collections import defaultdict

from .ai import analyze_article, analyze_china_deep_read
from .config import Settings
from .fetcher import fetch_candidates, fetch_china_candidates_with_meta
from .models import AnalyzedArticle, ChinaDeepRead
from .storage import load_recent_articles


DAILY_QUOTAS = {
    "World News": 2,
    "Technology & AI": 2,
    "Society & Culture": 2,
    "Business & Economy": 1,
}


FEATURE_CATEGORIES = {"Feature / Long Read", "English Learning"}


def generate_daily_articles(
    target_level: str, settings: Settings, feedback_note: str = ""
) -> tuple[list[AnalyzedArticle], list[str]]:
    recent_articles = load_recent_articles(keep=2)
    raw_articles, errors = fetch_candidates(
        timeout=min(settings.request_timeout, 20),
        per_source_limit=10,
        max_candidates=settings.max_candidates,
        recent_articles=recent_articles,
    )
    analyzed: list[AnalyzedArticle] = []

    for article in raw_articles:
        try:
            analyzed.append(
                analyze_article(
                    article,
                    target_level,
                    settings,
                    feedback_note=feedback_note,
                    model_override=settings.deepseek_daily_model,
                )
            )
        except Exception as exc:
            errors.append(f"{article.source} - {article.title}: {exc}")

    selected = select_daily_top(analyzed)
    return selected, errors


def generate_world_deep_read(
    articles: list[AnalyzedArticle],
    target_level: str,
    settings: Settings,
    feedback_note: str = "",
) -> tuple[AnalyzedArticle | None, list[str]]:
    errors: list[str] = []
    deep_read = select_deep_read(articles, articles)
    if deep_read:
        try:
            deep_read = analyze_article(
                deep_read,
                target_level,
                settings,
                feedback_note=feedback_note,
                model_override=settings.deepseek_deep_read_model,
            )
        except Exception as exc:
            errors.append(f"World Deep Read enhancement - {deep_read.title}: {exc}")
        deep_read.deep_read = True
    return deep_read, errors


def generate_briefing(
    target_level: str, settings: Settings, feedback_note: str = ""
) -> tuple[list[AnalyzedArticle], AnalyzedArticle | None, list[str]]:
    selected, errors = generate_daily_articles(target_level, settings, feedback_note=feedback_note)
    deep_read, deep_read_errors = generate_world_deep_read(
        selected,
        target_level,
        settings,
        feedback_note=feedback_note,
    )
    errors.extend(deep_read_errors)
    return selected, deep_read, errors


def generate_china_deep_read(settings: Settings) -> tuple[ChinaDeepRead | None, list[str]]:
    recent_articles = load_recent_articles(keep=2)
    candidates, meta, errors = fetch_china_candidates_with_meta(
        timeout=min(settings.request_timeout, 20),
        per_source_limit=20,
        max_candidates=80,
        ai_candidates=30,
        recent_articles=recent_articles,
    )
    try:
        deep_read = analyze_china_deep_read(candidates, settings, model_override=settings.deepseek_deep_read_model)
        if deep_read:
            deep_read.run_meta = meta
        return deep_read, errors
    except Exception as exc:
        errors.append(f"China Deep Read: {exc}")
        return None, errors


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
