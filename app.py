from __future__ import annotations

from datetime import date
from html import escape
from typing import Any
from urllib.parse import quote, unquote

import streamlit as st

from english_daily.briefing import generate_china_deep_read, generate_daily_articles, generate_world_deep_read
from english_daily.config import ensure_dirs, load_settings
from english_daily.export import briefing_to_markdown
from english_daily.models import AnalyzedArticle, ChinaDeepRead
from english_daily.sources import CATEGORIES, READING_LEVELS
from english_daily.storage import (
    build_feedback_note,
    list_saved_briefings,
    load_briefing_file,
    load_latest_briefing,
    load_saved_articles,
    load_user_marks,
    save_briefing,
    save_user_marks,
)


st.set_page_config(page_title="Daily English World Briefing", page_icon="E", layout="wide")


def inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
          --bg: #F6F7F9;
          --card: #FFFFFF;
          --text: #1F2933;
          --muted: #6B7280;
          --border: #E5E7EB;
          --border-strong: #CBD5E1;
          --accent: #2563EB;
          --accent-dark: #1E40AF;
          --slate: #334155;
          --green: #059669;
          --orange: #D97706;
          --red: #B45309;
        }
        .stApp {
          background: var(--bg);
          color: var(--text);
        }
        .block-container {
          max-width: 1280px;
          padding-top: 2rem;
          padding-bottom: 4rem;
        }
        section[data-testid="stSidebar"] {
          background: linear-gradient(180deg, #F8FAFC 0%, #EEF2F7 100%);
          border-right: 1px solid var(--border);
        }
        section[data-testid="stSidebar"] h2 {
          font-size: 1.05rem;
          line-height: 1.35;
          color: #0F172A;
          margin-bottom: 0.15rem;
        }
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stRadio p {
          color: #334155;
          font-weight: 650;
        }
        h1, h2, h3 {
          color: #111827;
          letter-spacing: 0;
        }
        h1 {
          font-size: 2rem;
          margin-bottom: 0.2rem;
        }
        h2 {
          font-size: 1.28rem;
          margin-top: 0.4rem;
        }
        .app-kicker {
          color: var(--muted);
          font-size: 0.92rem;
          margin-bottom: 1.1rem;
        }
        .summary-panel, .side-panel, .article-card, .deep-panel, .export-panel {
          background: var(--card);
          border: 1px solid var(--border);
          border-radius: 14px;
          box-shadow: 0 1px 2px rgba(15,23,42,0.04), 0 12px 30px rgba(15,23,42,0.03);
          padding: 18px 20px;
          margin-bottom: 18px;
        }
        .article-card {
          padding: 22px 24px;
          border-color: #E2E8F0;
          transition: border-color .16s ease, box-shadow .16s ease, transform .16s ease;
        }
        .article-card:hover {
          border-color: #B6C3D1;
          box-shadow: 0 2px 6px rgba(15,23,42,0.06), 0 16px 34px rgba(15,23,42,0.05);
          transform: translateY(-1px);
        }
        .deep-panel {
          padding: 26px 28px;
          border-top: 4px solid #334155;
        }
        .side-panel {
          position: sticky;
          top: 1.2rem;
          background: #FBFCFE;
        }
        .article-title {
          font-size: 1.2rem;
          font-weight: 700;
          line-height: 1.4;
          color: #111827;
          margin: 0.5rem 0 0.45rem;
        }
        .article-meta {
          font-size: 0.82rem;
          color: var(--muted);
          padding-bottom: 0.55rem;
          border-bottom: 1px solid #F1F5F9;
        }
        .section-label {
          font-size: 0.76rem;
          text-transform: uppercase;
          letter-spacing: .06em;
          color: var(--slate);
          font-weight: 700;
          margin-top: 0.95rem;
          margin-bottom: 0.38rem;
        }
        .english-summary {
          font-size: 0.98rem;
          line-height: 1.7;
          color: #1E293B;
          background: #FFFFFF;
          border-left: 3px solid #2563EB;
          padding: 10px 0 10px 14px;
        }
        .reason-text {
          color: #334155;
          line-height: 1.55;
          font-size: 0.95rem;
          background: #F8FAFC;
          border: 1px solid #E2E8F0;
          border-radius: 10px;
          padding: 10px 12px;
        }
        .chinese-context {
          font-size: 0.9rem;
          line-height: 1.6;
          color: #64748B;
          background: #F8FAFC;
          border-left: 3px solid #CBD5E1;
          padding: 10px 12px;
          border-radius: 8px;
          margin: 0.35rem 0 0.6rem;
        }
        .badge {
          display: inline-block;
          padding: 4px 9px;
          border-radius: 999px;
          font-size: 0.72rem;
          font-weight: 700;
          margin-right: 6px;
          margin-bottom: 4px;
          border: 1px solid transparent;
          vertical-align: middle;
        }
        .badge-blue {
          background: #EFF6FF;
          color: #1D4ED8;
          border-color: #BFDBFE;
        }
        .badge-slate {
          background: #F1F5F9;
          color: #334155;
          border-color: #CBD5E1;
        }
        .badge-green {
          background: #ECFDF5;
          color: var(--green);
          border-color: #A7F3D0;
        }
        .badge-orange {
          background: #FFF7ED;
          color: var(--orange);
          border-color: #FED7AA;
        }
        .action-hint {
          color: #64748B;
          font-size: 0.78rem;
          font-weight: 700;
          letter-spacing: .04em;
          text-transform: uppercase;
          border-top: 1px solid #E2E8F0;
          padding-top: 0.85rem;
          margin-top: 1rem;
        }
        .sidebar-status {
          background: rgba(255,255,255,0.72);
          border: 1px solid #DCE3EA;
          border-radius: 14px;
          padding: 12px 13px;
          margin: 0.4rem 0 0.75rem;
        }
        .status-row {
          display: flex;
          justify-content: space-between;
          gap: 12px;
          padding: 5px 0;
          border-bottom: 1px solid #EDF2F7;
          font-size: 0.82rem;
        }
        .status-row:last-child {
          border-bottom: 0;
        }
        .status-label {
          color: #64748B;
        }
        .status-value {
          color: #0F172A;
          font-weight: 700;
          text-align: right;
        }
        .mini-note {
          color: var(--muted);
          font-size: 0.86rem;
          line-height: 1.55;
        }
        .empty-state {
          background: #FFFFFF;
          border: 1px dashed #CBD5E1;
          border-radius: 14px;
          padding: 22px;
          color: var(--muted);
        }
        .stMetric {
          background: #FFFFFF;
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 12px 14px;
          box-shadow: 0 1px 2px rgba(15,23,42,0.035);
        }
        div[data-testid="stMetricValue"] {
          color: #0F172A;
          font-weight: 750;
        }
        div[data-testid="stMetricLabel"] {
          color: #64748B;
        }
        div.stButton > button,
        div.stDownloadButton > button,
        div.stLinkButton > a {
          min-height: 2.45rem;
          border-radius: 10px;
          border: 1px solid #CBD5E1;
          background: #FFFFFF;
          color: #1E293B;
          font-weight: 700;
          box-shadow: 0 1px 2px rgba(15,23,42,0.05);
          transition: all .14s ease;
        }
        div.stButton > button:hover,
        div.stDownloadButton > button:hover,
        div.stLinkButton > a:hover {
          border-color: #2563EB;
          color: #1D4ED8;
          background: #F8FAFF;
          box-shadow: 0 4px 12px rgba(37,99,235,0.12);
          transform: translateY(-1px);
        }
        div.stButton > button:active,
        div.stDownloadButton > button:active,
        div.stLinkButton > a:active {
          transform: translateY(0);
          box-shadow: 0 1px 3px rgba(15,23,42,0.08);
        }
        div.stButton > button[kind="primary"] {
          background: #1E40AF;
          color: #FFFFFF;
          border-color: #1E3A8A;
          box-shadow: 0 6px 16px rgba(30,64,175,0.22);
        }
        div.stButton > button[kind="primary"]:hover {
          background: #1D4ED8;
          color: #FFFFFF;
          border-color: #1D4ED8;
          box-shadow: 0 8px 20px rgba(29,78,216,0.26);
        }
        div[data-testid="stExpander"] {
          border: 1px solid #E2E8F0;
          border-radius: 12px;
          background: #FBFCFE;
        }
        div[data-testid="stExpander"] summary {
          color: #334155;
          font-weight: 650;
        }
        div[data-testid="stTabs"] button p {
          font-weight: 650;
        }
        div[data-testid="stTabs"] button {
          border-radius: 10px 10px 0 0;
        }
        div[data-testid="stAlert"] {
          border-radius: 12px;
        }
        div[data-baseweb="tag"] {
          background-color: #E2E8F0 !important;
          border: 1px solid #CBD5E1 !important;
          color: #334155 !important;
          border-radius: 999px !important;
        }
        div[data-baseweb="tag"] span {
          color: #334155 !important;
          font-weight: 650 !important;
        }
        div[data-baseweb="tag"] svg {
          color: #64748B !important;
        }
        div[data-baseweb="select"] > div {
          border-color: #CBD5E1 !important;
          border-radius: 12px !important;
          background: #FFFFFF !important;
        }
        div[data-testid="stPills"] button {
          background: #F8FAFC !important;
          border: 1px solid #CBD5E1 !important;
          color: #475569 !important;
          border-radius: 999px !important;
          font-weight: 700 !important;
          box-shadow: none !important;
        }
        div[data-testid="stPills"] button[aria-pressed="true"],
        div[data-testid="stPills"] button[kind="primary"] {
          background: #DBEAFE !important;
          border-color: #93C5FD !important;
          color: #1D4ED8 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="column"] div.stButton > button {
          min-height: 2.25rem;
          border-radius: 999px;
          box-shadow: none;
          font-size: 0.82rem;
        }
        section[data-testid="stSidebar"] div[data-testid="column"] div.stButton > button[kind="primary"] {
          background: #DBEAFE;
          color: #1D4ED8;
          border-color: #93C5FD;
          box-shadow: none;
        }
        section[data-testid="stSidebar"] div[data-testid="column"] div.stButton > button[kind="secondary"] {
          background: #F8FAFC;
          color: #64748B;
          border-color: #CBD5E1;
          box-shadow: none;
        }
        .category-pills {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin: 0.35rem 0 0.55rem;
        }
        .category-pill {
          display: inline-flex;
          align-items: center;
          min-height: 30px;
          padding: 5px 11px;
          border-radius: 999px;
          border: 1px solid #CBD5E1;
          background: #F8FAFC;
          color: #64748B !important;
          font-size: 0.78rem;
          font-weight: 750;
          text-decoration: none !important;
          line-height: 1.2;
          transition: all .14s ease;
        }
        .category-pill:hover {
          border-color: #94A3B8;
          background: #F1F5F9;
          color: #334155 !important;
        }
        .category-pill.active {
          background: #DBEAFE;
          border-color: #93C5FD;
          color: #1D4ED8 !important;
        }
        .category-pill.active:hover {
          background: #BFDBFE;
          border-color: #60A5FA;
          color: #1E40AF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def article_attr(article: AnalyzedArticle | None, name: str, fallback: Any = "") -> Any:
    if article is None:
        return fallback
    return getattr(article, name, fallback)


def saved_count() -> int:
    return sum(1 for item in st.session_state.get("marks", {}).values() if item.get("saved"))


def init_state() -> None:
    st.session_state.setdefault("articles", [])
    st.session_state.setdefault("deep_read", None)
    st.session_state.setdefault("china_deep_read", None)
    st.session_state.setdefault("deep_read_mode", "World")
    st.session_state.setdefault("errors", [])
    st.session_state.setdefault("marks", load_user_marks())
    st.session_state.setdefault("loaded_saved_briefing", False)
    st.session_state.setdefault("status_message", "")

    if not st.session_state["articles"] and not st.session_state["loaded_saved_briefing"]:
        saved = load_latest_briefing()
        st.session_state["loaded_saved_briefing"] = True
        if saved:
            articles, deep_read, deep_read_mode, china_deep_read = saved
            st.session_state["articles"] = articles
            st.session_state["deep_read"] = deep_read
            st.session_state["deep_read_mode"] = deep_read_mode
            st.session_state["china_deep_read"] = china_deep_read
            st.session_state["errors"] = []
            st.session_state["status_message"] = "Loaded from recent cache."


def mark_article(article: AnalyzedArticle, mark: str) -> None:
    marks = st.session_state["marks"]
    article_marks = marks.setdefault(article.link, {"too_easy": False, "too_hard": False, "saved": False})
    article_marks[mark] = not article_marks.get(mark, False)
    save_user_marks(marks)
    if mark == "saved":
        st.session_state["status_message"] = "Saved." if article_marks[mark] else "Removed from saved."
    elif mark == "too_easy":
        st.session_state["status_message"] = "Feedback recorded: too easy." if article_marks[mark] else "Too easy feedback removed."
    elif mark == "too_hard":
        st.session_state["status_message"] = "Feedback recorded: too hard." if article_marks[mark] else "Too hard feedback removed."


def load_saved_briefing(path_label: str, options: dict[str, object]) -> None:
    path = options.get(path_label)
    if not path:
        return
    loaded = load_briefing_file(path)
    if not loaded:
        return
    articles, deep_read, deep_read_mode, china_deep_read = loaded
    st.session_state["articles"] = articles
    st.session_state["deep_read"] = deep_read
    st.session_state["deep_read_mode"] = deep_read_mode
    st.session_state["china_deep_read"] = china_deep_read
    st.session_state["errors"] = []
    st.session_state["status_message"] = f"Loaded cached briefing: {path_label}."


def render_category_selector() -> list[str]:
    st.session_state.setdefault("visible_categories", CATEGORIES.copy())
    query_value = st.query_params.get("categories")
    if query_value:
        from_query = [unquote(item) for item in query_value.split(",") if item]
        current = [category for category in from_query if category in CATEGORIES]
        st.session_state["visible_categories"] = current
    else:
        current = [category for category in st.session_state["visible_categories"] if category in CATEGORIES]
        st.session_state["visible_categories"] = current

    st.sidebar.markdown("**Show categories**")
    st.sidebar.caption("Click a tag to show or hide that category.")

    selected_set = set(current)
    links = []
    for category in CATEGORIES:
        next_selected = [item for item in CATEGORIES if item in selected_set]
        if category in selected_set:
            next_selected = [item for item in next_selected if item != category]
        else:
            next_selected.append(category)
        encoded = ",".join(quote(item) for item in next_selected)
        active_class = " active" if category in selected_set else ""
        links.append(
            f'<a class="category-pill{active_class}" href="?categories={encoded}">{escape(category)}</a>'
        )

    st.sidebar.markdown(f'<div class="category-pills">{"".join(links)}</div>', unsafe_allow_html=True)
    return [item for item in CATEGORIES if item in selected_set]


def render_sidebar(settings: object) -> tuple[str, list[str], str, bool, bool]:
    st.sidebar.markdown("## Daily English World Briefing")
    st.sidebar.markdown('<p class="mini-note">English-first daily reading workspace.</p>', unsafe_allow_html=True)
    st.sidebar.caption(f"Today: {date.today().isoformat()}")
    st.sidebar.divider()

    target_level = st.sidebar.selectbox("Reading target", READING_LEVELS, index=1)
    current_mode = st.session_state.get("deep_read_mode", "World")
    deep_read_mode = st.sidebar.radio(
        "Deep Read Mode",
        ["World", "China"],
        index=1 if current_mode == "China" else 0,
        horizontal=True,
    )
    selected_categories = render_category_selector()

    st.sidebar.divider()
    saved_files = list_saved_briefings()
    if saved_files:
        labels = {path.name.replace("briefing-", "").replace(".json", ""): path for path in saved_files}
        selected_saved = st.sidebar.selectbox("Load cached briefing", list(labels.keys()))
        if st.sidebar.button("Load Cached Briefing"):
            load_saved_briefing(selected_saved, labels)
            st.rerun()
    else:
        st.sidebar.caption("No cached briefing yet.")

    generate_daily = st.sidebar.button("Generate Daily Top 8", type="primary", use_container_width=True)
    generate_deep_read = st.sidebar.button("Generate Deep Read", use_container_width=True)

    st.sidebar.divider()
    api_status = "configured" if getattr(settings, "deepseek_api_key", "") else "missing key"
    cache_status = "available" if saved_files else "not available"
    st.sidebar.markdown(
        f"""
        <div class="sidebar-status">
          <div class="status-row"><span class="status-label">Articles</span><span class="status-value">{len(st.session_state.get('articles', []))}</span></div>
          <div class="status-row"><span class="status-label">Saved</span><span class="status-value">{saved_count()}</span></div>
          <div class="status-row"><span class="status-label">Cache</span><span class="status-value">{cache_status}</span></div>
          <div class="status-row"><span class="status-label">API</span><span class="status-value">{api_status}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.get("status_message"):
        st.sidebar.success(st.session_state["status_message"])
    if not getattr(settings, "deepseek_api_key", ""):
        st.sidebar.warning("Missing DEEPSEEK_API_KEY. Create .env from .env.example before generating.")

    return target_level, selected_categories, deep_read_mode, generate_daily, generate_deep_read


def render_top_summary(
    articles: list[AnalyzedArticle],
    deep_read: AnalyzedArticle | None,
    china_deep_read: ChinaDeepRead | None,
    target_level: str,
    deep_read_mode: str,
) -> None:
    st.markdown('<div class="summary-panel">', unsafe_allow_html=True)
    st.markdown("# Today's Briefing")
    st.markdown(
        '<p class="app-kicker">8 selected articles for CET-6+ to IELTS 7 reading. '
        "English summaries stay primary; Chinese notes are support.</p>",
        unsafe_allow_html=True,
    )
    cols = st.columns(4)
    cols[0].metric("Articles", len(articles))
    cols[1].metric("Deep Read", 1 if (china_deep_read if deep_read_mode == "China" else deep_read) else 0)
    cols[2].metric("Saved", saved_count())
    cols[3].metric("Mode", f"{deep_read_mode} / {target_level}")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("errors"):
        with st.expander("Source/API warnings", expanded=False):
            for error in st.session_state["errors"]:
                st.warning(error)


def render_badges(article: AnalyzedArticle) -> None:
    importance = article_attr(article, "importance_score", 0)
    reading = article_attr(article, "reading_value_score", 0)
    st.markdown(
        f"""
        <span class="badge badge-blue">{safe_text(article_attr(article, "category"), "Uncategorized")}</span>
        <span class="badge badge-slate">{safe_text(article_attr(article, "level"), "Level N/A")}</span>
        <span class="badge badge-orange">Importance {importance}/10</span>
        <span class="badge badge-green">Reading {reading}/10</span>
        """,
        unsafe_allow_html=True,
    )


def render_article_actions(article: AnalyzedArticle, index: int, key_prefix: str) -> None:
    marks = st.session_state["marks"].get(article.link, {})
    st.markdown('<div class="action-hint">Actions</div>', unsafe_allow_html=True)
    col_open, col_save, col_easy, col_hard = st.columns([1.2, 1, 1, 1])
    with col_open:
        st.link_button("Open Original", article.link, use_container_width=True)
    with col_save:
        label = "Saved" if marks.get("saved") else "Save"
        if st.button(label, key=f"{key_prefix}-save-{index}-{article.link}", use_container_width=True):
            mark_article(article, "saved")
            st.rerun()
    with col_easy:
        label = "Too Easy" if not marks.get("too_easy") else "Too Easy (on)"
        if st.button(label, key=f"{key_prefix}-easy-{index}-{article.link}", use_container_width=True):
            mark_article(article, "too_easy")
            st.rerun()
    with col_hard:
        label = "Too Hard" if not marks.get("too_hard") else "Too Hard (on)"
        if st.button(label, key=f"{key_prefix}-hard-{index}-{article.link}", use_container_width=True):
            mark_article(article, "too_hard")
            st.rerun()


def render_article_card(article: AnalyzedArticle, index: int, key_prefix: str, compact: bool = False) -> None:
    st.markdown('<div class="article-card">', unsafe_allow_html=True)
    render_badges(article)
    st.markdown(f'<div class="article-title">{index}. {safe_text(article.title, "Untitled article")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="article-meta">{safe_text(article.source, "Unknown source")} | '
        f'{safe_text(article.published_time, "N/A")}</div>',
        unsafe_allow_html=True,
    )

    reason = safe_text(article.reason_to_read) or safe_text(article.why_it_matters)
    if reason:
        st.markdown('<div class="section-label">Why read it</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="reason-text">{reason}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-label">English summary</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="english-summary">{safe_text(article.english_summary, "No AI summary available.")}</div>', unsafe_allow_html=True)

    if not compact:
        if safe_text(article.thinking_question):
            st.markdown('<div class="section-label">Thinking question</div>', unsafe_allow_html=True)
            st.write(article.thinking_question)

        vocab = safe_list(article.core_vocabulary)
        if vocab:
            st.markdown('<div class="section-label">Vocabulary preview</div>', unsafe_allow_html=True)
            for item in vocab[:3]:
                if isinstance(item, dict) and item.get("word"):
                    st.markdown(f"- **{item.get('word', '')}**: {item.get('meaning_zh', '')}")
            if len(vocab) > 3:
                with st.expander("More vocabulary"):
                    render_vocabulary_items(vocab[3:])

        with st.expander("RSS summary"):
            st.write(safe_text(article.original_summary, "No RSS summary provided."))
        with st.expander("Article text from RSS/API"):
            if safe_text(article.article_text):
                st.write(article.article_text)
            else:
                st.caption("This source did not provide full article text through RSS/API. Use Open Original for the full article.")
        with st.expander("Chinese context"):
            st.markdown(f'<div class="chinese-context">{safe_text(article.chinese_context, "No Chinese context available.")}</div>', unsafe_allow_html=True)
        with st.expander("Useful expressions and sentence pattern"):
            expressions = safe_list(article.useful_expressions)
            if expressions:
                st.markdown("**Useful expressions**")
                for expression in expressions:
                    st.markdown(f"- {expression}")
            if safe_text(article.sentence_pattern):
                st.markdown("**Sentence pattern**")
                st.write(article.sentence_pattern)

    render_article_actions(article, index, key_prefix)
    st.markdown("</div>", unsafe_allow_html=True)


def render_vocabulary_items(items: list[Any]) -> None:
    for item in items:
        if isinstance(item, dict) and item.get("word"):
            st.markdown(f"- **{item.get('word', '')}**: {item.get('meaning_zh', '')}")
            if item.get("example"):
                st.caption(item["example"])


def render_language_notes(articles: list[AnalyzedArticle], deep_read: AnalyzedArticle | None) -> None:
    st.markdown('<div class="side-panel">', unsafe_allow_html=True)
    st.markdown("### Today's Language Notes")
    if not articles:
        st.caption("Generate a briefing to see today's reading plan and language notes.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown("**Reading plan**")
    st.markdown("- Start with two medium-length articles.")
    st.markdown("- Pick the Deep Read for focused reading.")
    st.markdown("- Save five reusable expressions.")

    categories = []
    for article in articles:
        category = safe_text(article.category)
        if category and category not in categories:
            categories.append(category)
    if categories:
        st.markdown("**Themes today**")
        for category in categories[:4]:
            st.markdown(f"- {category}")

    expressions: list[str] = []
    for article in articles:
        for expression in safe_list(article.useful_expressions):
            if expression and expression not in expressions:
                expressions.append(str(expression))
    if expressions:
        st.markdown("**Expression preview**")
        for expression in expressions[:5]:
            st.markdown(f"- {expression}")

    question = safe_text(article_attr(deep_read, "thinking_question"))
    if question:
        st.markdown("**Question to keep in mind**")
        st.write(question)
    st.markdown("</div>", unsafe_allow_html=True)


def render_today_tab(articles: list[AnalyzedArticle], selected_categories: list[str], deep_read: AnalyzedArticle | None) -> None:
    visible_articles = [article for article in articles if article.category in selected_categories]
    left, right = st.columns([2.2, 1])
    with left:
        st.markdown("## Daily Top 8")
        if not visible_articles:
            st.markdown(
                '<div class="empty-state">No articles to show. Generate today\'s briefing or adjust category filters.</div>',
                unsafe_allow_html=True,
            )
        for index, article in enumerate(visible_articles, start=1):
            render_article_card(article, index, "daily-top")
    with right:
        render_language_notes(visible_articles, deep_read)


def render_deep_read(article: AnalyzedArticle | None) -> None:
    st.markdown("## Today's Deep Read")
    if not article:
        st.markdown('<div class="empty-state">No Deep Read selected yet. Generate a briefing first.</div>', unsafe_allow_html=True)
        return

    st.markdown('<div class="deep-panel">', unsafe_allow_html=True)
    render_badges(article)
    st.markdown(f'<div class="article-title">{safe_text(article.title, "Untitled Deep Read")}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="article-meta">{safe_text(article.source)} | {safe_text(article.published_time, "N/A")}</div>',
        unsafe_allow_html=True,
    )
    if safe_text(article.why_it_matters):
        st.markdown('<div class="section-label">Why it matters</div>', unsafe_allow_html=True)
        st.write(article.why_it_matters)
    st.link_button("Open Original", article.link)

    left, right = st.columns([1.6, 1])
    with left:
        st.markdown('<div class="section-label">English summary</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="english-summary">{safe_text(article.english_summary, "No AI summary available.")}</div>', unsafe_allow_html=True)
        if safe_text(article.article_text):
            with st.expander("Article text from RSS/API"):
                st.write(article.article_text)
        with st.expander("Full RSS summary"):
            st.write(safe_text(article.original_summary, "No RSS summary provided."))
        if safe_text(article.sentence_pattern):
            st.markdown("**Sentence pattern**")
            st.write(article.sentence_pattern)
        expressions = safe_list(article.useful_expressions)
        if expressions:
            st.markdown("**Useful expressions**")
            for expression in expressions:
                st.markdown(f"- {expression}")
        if safe_text(article.thinking_question):
            st.markdown("**Thinking question**")
            st.write(article.thinking_question)

    with right:
        if safe_text(article.chinese_context):
            st.markdown("**Chinese context**")
            st.markdown(f'<div class="chinese-context">{article.chinese_context}</div>', unsafe_allow_html=True)
        if safe_list(article.deep_read_timeline):
            st.markdown("**Timeline**")
            for item in safe_list(article.deep_read_timeline):
                st.markdown(f"- {item}")
        if safe_list(article.key_actors):
            st.markdown("**Key actors**")
            for item in safe_list(article.key_actors):
                st.markdown(f"- {item}")
        if safe_text(article.main_tension):
            st.markdown("**Core conflict**")
            st.write(article.main_tension)
        if safe_list(article.writing_angles):
            st.markdown("**IELTS writing angles**")
            for item in safe_list(article.writing_angles):
                st.markdown(f"- {item}")
        vocab = safe_list(article.core_vocabulary)
        if vocab:
            st.markdown("**Vocabulary**")
            render_vocabulary_items(vocab)
        if safe_list(article.arguments_for) or safe_list(article.arguments_against):
            with st.expander("Different viewpoints"):
                st.markdown("**Perspective A**")
                for item in safe_list(article.arguments_for):
                    st.markdown(f"- {item}")
                st.markdown("**Perspective B**")
                for item in safe_list(article.arguments_against):
                    st.markdown(f"- {item}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_china_deep_read(china_deep_read: ChinaDeepRead | None) -> None:
    st.markdown("## China Deep Read")
    if not china_deep_read:
        st.markdown(
            '<div class="empty-state">No China Deep Read yet. Select China mode, then click Generate Deep Read.</div>',
            unsafe_allow_html=True,
        )
        return

    st.markdown('<div class="deep-panel">', unsafe_allow_html=True)
    st.markdown('<span class="badge badge-blue">China</span><span class="badge badge-slate">中文信息获取</span>', unsafe_allow_html=True)
    st.markdown(f'<div class="article-title">{safe_text(china_deep_read.headline, "中国深读")}</div>', unsafe_allow_html=True)
    if safe_text(china_deep_read.source_summary):
        st.markdown(f'<div class="article-meta">{china_deep_read.source_summary}</div>', unsafe_allow_html=True)

    run_meta = china_deep_read.run_meta if isinstance(china_deep_read.run_meta, dict) else {}
    if run_meta:
        meta_cols = st.columns(4)
        meta_cols[0].metric("Fetched", run_meta.get("raw_fetched_count", 0))
        meta_cols[1].metric("Deduped", run_meta.get("deduped_count", 0))
        meta_cols[2].metric("Candidate Pool", run_meta.get("candidate_pool_count", 0))
        meta_cols[3].metric("Sent to Pro", run_meta.get("sent_to_ai_count", 0))

    left, right = st.columns([1.6, 1])
    with left:
        st.markdown('<div class="section-label">为什么重要</div>', unsafe_allow_html=True)
        st.write(safe_text(china_deep_read.why_it_matters, "暂无说明。"))
        st.markdown('<div class="section-label">发生了什么</div>', unsafe_allow_html=True)
        st.write(safe_text(china_deep_read.what_happened, "暂无概述。"))
        st.markdown('<div class="section-label">公共影响</div>', unsafe_allow_html=True)
        st.write(safe_text(china_deep_read.public_impact, "暂无公共影响分析。"))
        if safe_text(china_deep_read.social_or_economic_issue):
            st.markdown('<div class="section-label">社会/经济问题</div>', unsafe_allow_html=True)
            st.write(china_deep_read.social_or_economic_issue)
        if safe_text(china_deep_read.critical_angle):
            st.markdown('<div class="section-label">批判性观察</div>', unsafe_allow_html=True)
            st.write(china_deep_read.critical_angle)

    with right:
        if safe_text(china_deep_read.background):
            st.markdown("**背景**")
            st.write(china_deep_read.background)
        if safe_list(china_deep_read.timeline):
            st.markdown("**时间线**")
            for item in safe_list(china_deep_read.timeline):
                st.markdown(f"- {item}")
        if safe_list(china_deep_read.key_actors):
            st.markdown("**关键主体**")
            for item in safe_list(china_deep_read.key_actors):
                st.markdown(f"- {item}")
        if safe_text(china_deep_read.propaganda_risk):
            st.markdown("**宣传风险判断**")
            st.write(china_deep_read.propaganda_risk)

    if safe_list(china_deep_read.different_angles):
        with st.expander("不同观察角度", expanded=True):
            for item in safe_list(china_deep_read.different_angles):
                st.markdown(f"- {item}")
    if safe_list(china_deep_read.uncertainties):
        with st.expander("仍需观察的不确定信息"):
            for item in safe_list(china_deep_read.uncertainties):
                st.markdown(f"- {item}")
    if safe_list(china_deep_read.links):
        st.markdown("**来源链接**")
        for item in safe_list(china_deep_read.links):
            if isinstance(item, dict) and item.get("url"):
                label = safe_text(item.get("title"), item.get("url"))
                source = safe_text(item.get("source"))
                st.markdown(f"- [{label}]({item.get('url')}) {f'({source})' if source else ''}")
    st.markdown("</div>", unsafe_allow_html=True)


def render_vocabulary_section(articles: list[AnalyzedArticle]) -> None:
    st.markdown("## Vocabulary")
    if not articles:
        st.markdown('<div class="empty-state">No vocabulary yet. Generate a briefing first.</div>', unsafe_allow_html=True)
        return

    vocab_rows: list[dict[str, str]] = []
    expressions: list[tuple[str, str]] = []
    patterns: list[tuple[str, str]] = []
    for article in articles:
        title = safe_text(article.title, "Untitled")
        for item in safe_list(article.core_vocabulary):
            if isinstance(item, dict) and item.get("word"):
                vocab_rows.append(
                    {
                        "Word": safe_text(item.get("word")),
                        "Meaning": safe_text(item.get("meaning_zh")),
                        "Example": safe_text(item.get("example")),
                        "Source": title,
                    }
                )
        for expression in safe_list(article.useful_expressions):
            if expression:
                expressions.append((str(expression), title))
        if safe_text(article.sentence_pattern):
            patterns.append((article.sentence_pattern, title))

    core_tab, expression_tab, pattern_tab = st.tabs(["Core Vocabulary", "Useful Expressions", "Sentence Patterns"])
    with core_tab:
        if vocab_rows:
            st.dataframe(vocab_rows, hide_index=True, use_container_width=True)
        else:
            st.caption("No vocabulary items available.")
    with expression_tab:
        if expressions:
            cols = st.columns(2)
            for index, (expression, source) in enumerate(expressions):
                with cols[index % 2]:
                    st.markdown('<div class="side-panel">', unsafe_allow_html=True)
                    st.markdown(f"**{expression}**")
                    st.caption(source)
                    st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("No useful expressions available.")
    with pattern_tab:
        if patterns:
            for index, (pattern, source) in enumerate(patterns, start=1):
                with st.expander(f"Pattern {index}: {source}", expanded=index <= 2):
                    st.write(pattern)
        else:
            st.caption("No sentence patterns available.")
    st.caption("Vocabulary-only export is not enabled yet; use the Export tab for the full Markdown briefing.")


def render_saved_articles() -> None:
    st.markdown("## Saved Articles")
    saved_articles = load_saved_articles()
    saved_links = [link for link, item_marks in st.session_state["marks"].items() if item_marks.get("saved")]

    if not saved_links:
        st.markdown(
            '<div class="empty-state">No saved articles yet. Save articles from Today\'s Briefing to build your personal reading library.</div>',
            unsafe_allow_html=True,
        )
        return

    if not saved_articles:
        st.info("Saved links exist, but matching article details are no longer in the two-day cache.")
        for link in saved_links:
            st.markdown(f"- [{link}]({link})")
        return

    found_links = {article.link for article in saved_articles}
    for index, article in enumerate(saved_articles, start=1):
        render_article_card(article, index, "saved", compact=True)
        with st.expander(f"Learning details: {safe_text(article.title, 'Saved article')}"):
            st.markdown("**Chinese context**")
            st.write(safe_text(article.chinese_context, "No Chinese context available."))
            st.markdown("**Vocabulary**")
            render_vocabulary_items(safe_list(article.core_vocabulary))
            st.markdown("**Useful expressions**")
            for expression in safe_list(article.useful_expressions):
                st.markdown(f"- {expression}")
            if safe_text(article.sentence_pattern):
                st.markdown("**Sentence pattern**")
                st.write(article.sentence_pattern)

    missing_links = [link for link in saved_links if link not in found_links]
    if missing_links:
        with st.expander("Older saved links outside the two-day cache"):
            for link in missing_links:
                st.markdown(f"- [{link}]({link})")


def render_export_panel(
    articles: list[AnalyzedArticle],
    deep_read: AnalyzedArticle | None,
    target_level: str,
    deep_read_mode: str,
    china_deep_read: ChinaDeepRead | None,
) -> None:
    st.markdown("## Export")
    st.markdown('<div class="export-panel">', unsafe_allow_html=True)
    st.markdown(f"**Export date:** {date.today().isoformat()}")
    st.markdown("**Included content**")
    st.markdown("- Daily Top 8")
    st.markdown(f"- Today's Deep Read ({deep_read_mode})")
    st.markdown("- Vocabulary, expressions, sentence patterns")
    st.markdown("- Thinking questions")
    st.markdown("- RSS/API article text when legally provided by the source")
    if china_deep_read:
        st.markdown("- China Deep Read Chinese information brief")

    if not articles and not china_deep_read:
        st.caption("No briefing loaded. Generate or load a cached briefing before exporting.")
    else:
        export_deep_read = None if deep_read_mode == "China" else deep_read
        markdown = briefing_to_markdown(articles, export_deep_read, target_level) if articles else ""
        if deep_read_mode == "China" and china_deep_read:
            markdown += "\n\n" + china_deep_read_to_markdown(china_deep_read)
        st.download_button(
            "Export Markdown",
            data=markdown,
            file_name="daily-english-world-briefing.md",
            mime="text/markdown",
            use_container_width=True,
        )
        if deep_read_mode == "China" and china_deep_read and china_deep_read.run_meta:
            with st.expander("China Deep Read run details"):
                st.json(china_deep_read.run_meta)
    st.markdown("</div>", unsafe_allow_html=True)


def china_deep_read_to_markdown(china_deep_read: ChinaDeepRead) -> str:
    lines = [
        "# China Deep Read",
        "",
        f"## {china_deep_read.headline}",
        "",
        f"来源概览：{china_deep_read.source_summary}",
        "",
        f"为什么重要：{china_deep_read.why_it_matters}",
        "",
        f"发生了什么：{china_deep_read.what_happened}",
        "",
        f"背景：{china_deep_read.background}",
        "",
        f"公共影响：{china_deep_read.public_impact}",
        "",
        f"社会/经济问题：{china_deep_read.social_or_economic_issue}",
        "",
        f"批判性观察：{china_deep_read.critical_angle}",
        "",
        "## 时间线",
    ]
    lines.extend(f"- {item}" for item in safe_list(china_deep_read.timeline))
    lines.append("")
    lines.append("## 来源链接")
    for item in safe_list(china_deep_read.links):
        if isinstance(item, dict) and item.get("url"):
            lines.append(f"- [{safe_text(item.get('title'), item.get('url'))}]({item.get('url')})")
    return "\n".join(lines)


def china_deep_read_to_markdown(china_deep_read: ChinaDeepRead) -> str:
    lines = [
        "# China Deep Read",
        "",
        f"## {china_deep_read.headline}",
        "",
        f"Source summary: {china_deep_read.source_summary}",
        "",
        f"Why it matters: {china_deep_read.why_it_matters}",
        "",
        f"What happened: {china_deep_read.what_happened}",
        "",
        f"Background: {china_deep_read.background}",
        "",
        f"Public impact: {china_deep_read.public_impact}",
        "",
        f"Social / economic issue: {china_deep_read.social_or_economic_issue}",
        "",
        f"Critical angle: {china_deep_read.critical_angle}",
        "",
        "## Run Details",
        "",
        f"- Raw fetched: {china_deep_read.run_meta.get('raw_fetched_count', 0)}",
        f"- Deduped: {china_deep_read.run_meta.get('deduped_count', 0)}",
        f"- Candidate pool: {china_deep_read.run_meta.get('candidate_pool_count', 0)}",
        f"- Sent to Pro: {china_deep_read.run_meta.get('sent_to_ai_count', 0)}",
        "",
        "## Timeline",
    ]
    lines.extend(f"- {item}" for item in safe_list(china_deep_read.timeline))
    lines.append("")
    lines.append("## Source Links")
    for item in safe_list(china_deep_read.links):
        if isinstance(item, dict) and item.get("url"):
            lines.append(f"- [{safe_text(item.get('title'), item.get('url'))}]({item.get('url')})")
    return "\n".join(lines)


def main() -> None:
    ensure_dirs()
    inject_css()
    init_state()
    settings = load_settings()

    target_level, selected_categories, deep_read_mode, generate_daily, generate_deep_read = render_sidebar(settings)

    if generate_daily:
        with st.spinner("Fetching RSS feeds and asking DeepSeek Flash to score Daily Top 8 candidates..."):
            articles, errors = generate_daily_articles(target_level, settings, feedback_note=build_feedback_note())
            st.session_state["articles"] = articles
            st.session_state["deep_read_mode"] = deep_read_mode
            st.session_state["errors"] = errors
            if articles:
                save_briefing(
                    articles,
                    st.session_state.get("deep_read"),
                    deep_read_mode=deep_read_mode,
                    china_deep_read=st.session_state.get("china_deep_read"),
                )
                st.session_state["status_message"] = "Generated Daily Top 8."
            else:
                st.session_state["status_message"] = "No Daily Top 8 articles generated. Check Source/API warnings."

    if generate_deep_read:
        st.session_state["deep_read_mode"] = deep_read_mode
        if deep_read_mode == "China":
            with st.spinner("Building China Deep Read with DeepSeek Pro..."):
                china_deep_read, errors = generate_china_deep_read(settings)
                st.session_state["china_deep_read"] = china_deep_read
                st.session_state["errors"] = errors
                if china_deep_read:
                    save_briefing(
                        st.session_state.get("articles", []),
                        st.session_state.get("deep_read"),
                        deep_read_mode=deep_read_mode,
                        china_deep_read=china_deep_read,
                    )
                    st.session_state["status_message"] = "Generated China Deep Read."
                else:
                    st.session_state["status_message"] = "No China Deep Read generated. Check Source/API warnings."
        else:
            current_articles: list[AnalyzedArticle] = st.session_state.get("articles", [])
            if not current_articles:
                st.session_state["errors"] = []
                st.session_state["status_message"] = "Generate Daily Top 8 first, then build World Deep Read."
            else:
                with st.spinner("Building World Deep Read with DeepSeek Pro..."):
                    deep_read, errors = generate_world_deep_read(
                        current_articles,
                        target_level,
                        settings,
                        feedback_note=build_feedback_note(),
                    )
                    st.session_state["deep_read"] = deep_read
                    st.session_state["errors"] = errors
                    if deep_read:
                        save_briefing(
                            current_articles,
                            deep_read,
                            deep_read_mode=deep_read_mode,
                            china_deep_read=st.session_state.get("china_deep_read"),
                        )
                        st.session_state["status_message"] = "Generated World Deep Read."
                    else:
                        st.session_state["status_message"] = "No World Deep Read generated. Check Source/API warnings."

    articles: list[AnalyzedArticle] = st.session_state["articles"]
    deep_read: AnalyzedArticle | None = st.session_state["deep_read"]
    china_deep_read: ChinaDeepRead | None = st.session_state["china_deep_read"]
    active_deep_read_mode = deep_read_mode or st.session_state.get("deep_read_mode", "World")
    st.session_state["deep_read_mode"] = active_deep_read_mode
    render_top_summary(articles, deep_read, china_deep_read, target_level, active_deep_read_mode)

    today_tab, deep_tab, vocab_tab, saved_tab, export_tab = st.tabs(["Today", "Deep Read", "Vocabulary", "Saved", "Export"])
    with today_tab:
        render_today_tab(articles, selected_categories, deep_read)
    with deep_tab:
        if active_deep_read_mode == "China":
            render_china_deep_read(china_deep_read)
        else:
            render_deep_read(deep_read)
    with vocab_tab:
        render_vocabulary_section(articles)
    with saved_tab:
        render_saved_articles()
    with export_tab:
        render_export_panel(articles, deep_read, target_level, active_deep_read_mode, china_deep_read)


if __name__ == "__main__":
    main()
