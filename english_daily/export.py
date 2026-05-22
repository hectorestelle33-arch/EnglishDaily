from __future__ import annotations

from datetime import date

from .models import AnalyzedArticle


def briefing_to_markdown(articles: list[AnalyzedArticle], deep_read: AnalyzedArticle | None, target_level: str) -> str:
    lines = [
        f"# Daily English World Briefing - {date.today().isoformat()}",
        "",
        f"Reading target: **{target_level}**",
        "",
    ]

    if deep_read:
        lines.extend(
            [
                "## Today's Deep Read",
                f"### [{deep_read.title}]({deep_read.link})",
                f"- Source: {deep_read.source}",
                f"- Category: {deep_read.category}",
                f"- Level: {deep_read.level}",
                f"- Scores: importance {deep_read.importance_score}/10, reading value {deep_read.reading_value_score}/10",
                "",
                deep_read.english_summary,
                "",
                f"Chinese context: {deep_read.chinese_context}",
                "",
                f"Main tension: {deep_read.main_tension}",
                "",
                "Background timeline: " + "; ".join(deep_read.deep_read_timeline),
                "Key actors: " + "; ".join(deep_read.key_actors),
                "Reusable writing angles: " + "; ".join(deep_read.writing_angles),
                "",
            ]
        )

    lines.append("## Daily Top 8")
    for index, article in enumerate(articles, start=1):
        lines.extend(article_to_markdown(index, article))
    return "\n".join(lines)


def article_to_markdown(index: int, article: AnalyzedArticle) -> list[str]:
    vocab = "; ".join(
        f"{item.get('word', '')}: {item.get('meaning_zh', '')}" for item in article.core_vocabulary if item.get("word")
    )
    expressions = "; ".join(article.useful_expressions)
    return [
        "",
        f"### {index}. [{article.title}]({article.link})",
        f"- Source: {article.source}",
        f"- Published: {article.published_time or 'N/A'}",
        f"- Category: {article.category}",
        f"- Level: {article.level}",
        f"- Scores: importance {article.importance_score}/10, reading value {article.reading_value_score}/10",
        f"- Why it matters: {article.why_it_matters}",
        f"- Reason to read: {article.reason_to_read}",
        "",
        f"Original summary: {article.original_summary}",
        "",
        f"Article text from RSS/API: {article.article_text or 'Not provided by this RSS/API source.'}",
        "",
        f"English summary: {article.english_summary}",
        "",
        f"Chinese context: {article.chinese_context}",
        "",
        f"Core vocabulary: {vocab}",
        f"Useful expressions: {expressions}",
        f"Sentence pattern: {article.sentence_pattern}",
        f"Thinking question: {article.thinking_question}",
    ]
