from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawArticle:
    title: str
    source: str
    category: str
    link: str
    published_time: str
    original_summary: str
    article_text: str = ""


@dataclass
class AnalyzedArticle:
    title: str
    source: str
    published_time: str
    category: str
    link: str
    original_summary: str
    level: str
    importance_score: int
    reading_value_score: int
    why_it_matters: str
    reason_to_read: str
    english_summary: str
    chinese_context: str
    article_text: str = ""
    core_vocabulary: list[dict[str, str]] = field(default_factory=list)
    useful_expressions: list[str] = field(default_factory=list)
    sentence_pattern: str = ""
    thinking_question: str = ""
    deep_read_timeline: list[str] = field(default_factory=list)
    key_actors: list[str] = field(default_factory=list)
    main_tension: str = ""
    arguments_for: list[str] = field(default_factory=list)
    arguments_against: list[str] = field(default_factory=list)
    writing_angles: list[str] = field(default_factory=list)
    filter_out: bool = False
    deep_read: bool = False
    raw_ai: dict[str, Any] = field(default_factory=dict)
