from __future__ import annotations

from dataclasses import dataclass


CATEGORIES = [
    "World News",
    "Technology & AI",
    "Business & Economy",
    "Society & Culture",
    "Feature / Long Read",
    "English Learning",
]

READING_LEVELS = ["CET-6+", "IELTS 7", "Challenge C1-"]


@dataclass(frozen=True)
class NewsSource:
    name: str
    category: str
    feed_url: str


RSS_SOURCES = [
    NewsSource("BBC News", "World News", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    NewsSource("BBC Business", "Business & Economy", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    NewsSource("UN News", "World News", "https://news.un.org/feed/subscribe/en/news/all/rss.xml"),
    NewsSource("Al Jazeera", "World News", "https://www.aljazeera.com/xml/rss/all.xml"),
    NewsSource("AP News", "World News", "https://apnews.com/hub/world-news?output=rss"),
    NewsSource("The Guardian World", "World News", "https://www.theguardian.com/world/rss"),
    NewsSource("The Guardian Culture", "Society & Culture", "https://www.theguardian.com/culture/rss"),
    NewsSource("NPR World", "World News", "https://feeds.npr.org/1004/rss.xml"),
    NewsSource("NPR Culture", "Society & Culture", "https://feeds.npr.org/1008/rss.xml"),
    NewsSource("MIT Technology Review", "Technology & AI", "https://www.technologyreview.com/feed/"),
    NewsSource("The Verge", "Technology & AI", "https://www.theverge.com/rss/index.xml"),
    NewsSource("VOA Learning English", "English Learning", "https://learningenglish.voanews.com/api/epiqq"),
    NewsSource("VOA Science & Technology", "English Learning", "https://learningenglish.voanews.com/api/zmg_pe$myp"),
]
