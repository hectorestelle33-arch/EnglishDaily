from __future__ import annotations

import json
import re
from typing import Any

import requests

from .config import Settings
from .models import AnalyzedArticle, ChinaDeepRead, RawArticle


DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"


SYSTEM_PROMPT = """You are an editor for a personal Daily English World Briefing.
Your job is to select high-quality English world news for a reader training from CET-6+ to IELTS 7.
Do not simplify news English too much. Keep the tone close to real international journalism.
Filter out sports scores, celebrity gossip, tiny local items, short-term stock movement, duplicate or low-context stories, and items with too little summary.
Return strict JSON only."""


def analyze_article(
    article: RawArticle,
    target_level: str,
    settings: Settings,
    feedback_note: str = "",
    model_override: str | None = None,
) -> AnalyzedArticle:
    if not settings.deepseek_api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY. Create a .env file from .env.example first.")

    payload = {
        "model": model_override or settings.deepseek_model,
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
    if payload["model"].startswith("deepseek-v4-"):
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


def analyze_china_deep_read(
    articles: list[RawArticle], settings: Settings, model_override: str | None = None
) -> ChinaDeepRead | None:
    if not settings.deepseek_api_key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY. Create a .env file from .env.example first.")
    if not articles:
        return None

    payload = {
        "model": model_override or settings.deepseek_deep_read_model,
        "temperature": 0.15,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "你是一个克制、客观的中文新闻编辑，负责从候选新闻中选择最值得深入了解的一条中国社会/民生/经济议题。只返回严格 JSON。",
            },
            {"role": "user", "content": build_china_deep_read_prompt(articles)},
        ],
    }
    if payload["model"].startswith("deepseek-v4-"):
        payload["thinking"] = {"type": normalize_thinking_mode(settings.deepseek_thinking)}

    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(DEEPSEEK_CHAT_URL, headers=headers, json=payload, timeout=settings.request_timeout)
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    data = parse_json_object(content)
    if bool(data.get("filter_out", False)):
        return None
    return normalize_china_deep_read(data)


def build_china_deep_read_prompt(articles: list[RawArticle]) -> str:
    candidates = []
    for index, article in enumerate(articles[:24], start=1):
        candidates.append(
            {
                "id": index,
                "title": article.title,
                "source": article.source,
                "published_time": article.published_time,
                "link": article.link,
                "summary": article.original_summary,
            }
        )
    return f"""
请从以下中文新闻候选中，选择最适合做 China Deep Read 的一条或一个同一事件簇。

目标：
- 这是中文信息获取区，不是英语学习区。
- 关注中国当日或昨日最重要的民生、社会、经济、公共政策信息。
- 优先选择与普通人生活、就业、收入、医疗、教育、养老、住房、消费、社会问题、经济压力相关的内容。
- 有批判性、揭露社会问题、呈现现实矛盾、公共影响清晰的内容优先。

需要降权或过滤：
- 明显宣传成就、捷报、正面典型宣传。
- 为展现中国进步、中国速度、中国力量而写的宏大叙事。
- 领导活动通稿。
- 缺少具体社会影响的建设成果、技术突破、国际赞誉。

候选新闻 JSON：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

返回严格 JSON：
{{
  "headline": "中文标题",
  "source_summary": "主要来源和来源差异，1-2句",
  "why_it_matters": "为什么重要，偏公共影响",
  "what_happened": "发生了什么，客观概述",
  "background": "必要背景",
  "timeline": ["3-5个关键时间点或事件推进"],
  "key_actors": ["关键机构、群体、地区或人物"],
  "public_impact": "对普通人、经济、政策或社会的影响",
  "social_or_economic_issue": "这条新闻反映的社会或经济问题",
  "critical_angle": "克制、有依据的批判性观察角度",
  "different_angles": ["2-4个不同观察角度"],
  "uncertainties": ["仍不确定或需要继续观察的信息"],
  "propaganda_risk": "low | medium | high，并简述原因",
  "filter_out": false,
  "filter_out_reason": "",
  "links": [{{"title": "来源标题", "source": "来源", "url": "链接"}}]
}}

如果所有候选都明显宣传化、缺少公共影响或不适合深读，请设置 filter_out=true 并说明 filter_out_reason。
输出必须客观、克制，不要情绪化评论。
"""


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


def normalize_china_deep_read(data: dict[str, Any]) -> ChinaDeepRead:
    return ChinaDeepRead(
        headline=str(data.get("headline") or ""),
        source_summary=str(data.get("source_summary") or ""),
        why_it_matters=str(data.get("why_it_matters") or ""),
        what_happened=str(data.get("what_happened") or ""),
        background=str(data.get("background") or ""),
        public_impact=str(data.get("public_impact") or ""),
        social_or_economic_issue=str(data.get("social_or_economic_issue") or ""),
        critical_angle=str(data.get("critical_angle") or ""),
        propaganda_risk=str(data.get("propaganda_risk") or ""),
        filter_out_reason=str(data.get("filter_out_reason") or ""),
        timeline=normalize_string_list(data.get("timeline"), 5),
        key_actors=normalize_string_list(data.get("key_actors"), 8),
        different_angles=normalize_string_list(data.get("different_angles"), 4),
        uncertainties=normalize_string_list(data.get("uncertainties"), 4),
        links=normalize_links(data.get("links")),
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


def normalize_links(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    links: list[dict[str, str]] = []
    for item in value[:6]:
        if isinstance(item, dict):
            links.append(
                {
                    "title": str(item.get("title") or ""),
                    "source": str(item.get("source") or ""),
                    "url": str(item.get("url") or ""),
                }
            )
    return links
