from __future__ import annotations

import json
import re
from typing import Any

import requests

from .config import Settings
from .models import AnalyzedArticle, RawArticle


DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"


SYSTEM_PROMPT = """You are an editor for a personal Daily English World Briefing.
Your job is to select high-quality English world news for a reader training from CET-6+ to IELTS 7.
Do not simplify news English too much. Keep the tone close to real international journalism.
Filter out sports scores, celebrity gossip, tiny local items, short-term stock movement, duplicate or low-context stories, and items with too little summary.
Return strict JSON only."""


def analyze_article(
    article: RawArticle, target_level: str, settings: Settings, feedback_note: str = ""
) -> AnalyzedArticle:
    if not settings.deepseek_api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY. Create a .env file from .env.example first.")

    payload = {
        "model": settings.deepseek_model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_user_prompt(article, target_level, feedback_note),
            },
        ],
    }
    if settings.deepseek_model.startswith("deepseek-v4-"):
        payload["thinking"] = {"type": normalize_thinking_mode(settings.deepseek_thinking)}

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(DEEPSEEK_CHAT_URL, headers=headers, json=payload, timeout=settings.request_timeout)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    data = parse_json_object(content)
    return normalize_analysis(article, data)


def build_user_prompt(article: RawArticle, target_level: str, feedback_note: str = "") -> str:
    article_text_section = (
        f"- article_text_from_rss_or_api: {article.article_text[:4000]}"
        if article.article_text
        else "- article_text_from_rss_or_api: Not provided by this RSS/API source."
    )
    return f"""
Analyze this RSS news item for a Daily English World Briefing.

Reader target level: {target_level}
Prior reader feedback for calibration: {feedback_note or "No prior difficulty feedback yet."}

Article:
- title: {article.title}
- source: {article.source}
- source_category: {article.category}
- published_time: {article.published_time}
- link: {article.link}
- original_summary: {article.original_summary}
{article_text_section}

Use prior feedback to calibrate difficulty:
- If similar saved articles were marked too easy, prefer richer vocabulary, denser summaries, and Challenge C1- when justified.
- If similar saved articles were marked too hard, keep IELTS 7/CET-6+ accessible and add clearer context.

Return exactly this JSON object:
{{
  "category": "World News | Technology & AI | Business & Economy | Society & Culture | Feature / Long Read | English Learning",
  "level": "CET-6+ | IELTS 7 | Challenge C1-",
  "importance_score": 1,
  "reading_value_score": 1,
  "filter_out": false,
  "why_it_matters": "1-2 English sentences explaining the real-world significance.",
  "reason_to_read": "1 English sentence explaining why this is worth reading for an English learner.",
  "english_summary": "About 120 words, in authentic news English suitable for CET-6+ to IELTS 7, not oversimplified.",
  "chinese_context": "80-120 Chinese characters. Context only; do not replace English reading.",
  "core_vocabulary": [
    {{"word": "word", "meaning_zh": "中文释义", "example": "short English example sentence"}}
  ],
  "useful_expressions": ["expression 1", "expression 2", "expression 3"],
  "sentence_pattern": "A useful sentence pattern from news English with a short example.",
  "thinking_question": "One open-ended English discussion question.",
  "deep_read_timeline": ["3-5 concise timeline points if this article becomes the deep read"],
  "key_actors": ["3-6 key people, institutions, countries, or companies"],
  "main_tension": "One sentence explaining the central conflict, tradeoff, or uncertainty.",
  "arguments_for": ["2-3 arguments or perspectives supporting one side"],
  "arguments_against": ["2-3 arguments or perspectives supporting another side"],
  "writing_angles": ["2-3 IELTS-style writing or speaking angles a learner could reuse"]
}}

Vocabulary must contain exactly 5 items. Expressions must contain exactly 3 items.
Deep-read fields should be useful but concise, even for non-deep-read candidates.
If the item should be filtered out, still fill the fields briefly and set filter_out to true.
"""


def parse_json_object(content: str) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_thinking_mode(value: str) -> str:
    if value in {"enabled", "disabled", "auto"}:
        return value
    return "disabled"


def normalize_analysis(article: RawArticle, data: dict[str, Any]) -> AnalyzedArticle:
    return AnalyzedArticle(
        title=article.title,
        source=article.source,
        published_time=article.published_time,
        category=str(data.get("category") or article.category),
        link=article.link,
        original_summary=article.original_summary,
        article_text=article.article_text,
        level=str(data.get("level") or "IELTS 7"),
        importance_score=clamp_score(data.get("importance_score")),
        reading_value_score=clamp_score(data.get("reading_value_score")),
        why_it_matters=str(data.get("why_it_matters") or ""),
        reason_to_read=str(data.get("reason_to_read") or ""),
        english_summary=str(data.get("english_summary") or ""),
        chinese_context=str(data.get("chinese_context") or ""),
        core_vocabulary=normalize_vocab(data.get("core_vocabulary")),
        useful_expressions=normalize_string_list(data.get("useful_expressions"), 3),
        sentence_pattern=str(data.get("sentence_pattern") or ""),
        thinking_question=str(data.get("thinking_question") or ""),
        deep_read_timeline=normalize_string_list(data.get("deep_read_timeline"), 5),
        key_actors=normalize_string_list(data.get("key_actors"), 6),
        main_tension=str(data.get("main_tension") or ""),
        arguments_for=normalize_string_list(data.get("arguments_for"), 3),
        arguments_against=normalize_string_list(data.get("arguments_against"), 3),
        writing_angles=normalize_string_list(data.get("writing_angles"), 3),
        filter_out=bool(data.get("filter_out", False)),
        raw_ai=data,
    )


def clamp_score(value: Any) -> int:
    try:
        return max(1, min(10, int(value)))
    except (TypeError, ValueError):
        return 1


def normalize_vocab(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, str]] = []
    for item in value[:5]:
        if isinstance(item, dict):
            items.append(
                {
                    "word": str(item.get("word") or ""),
                    "meaning_zh": str(item.get("meaning_zh") or ""),
                    "example": str(item.get("example") or ""),
                }
            )
        else:
            items.append({"word": str(item), "meaning_zh": "", "example": ""})
    return items


def normalize_string_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value[:limit]]
