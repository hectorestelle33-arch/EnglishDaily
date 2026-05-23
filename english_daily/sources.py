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


CHINA_DEEP_READ_SOURCES = [
    NewsSource("中新网时政", "China Deep Read", "https://www.chinanews.com.cn/rss/china.xml"),
    NewsSource("中新网社会", "China Deep Read", "https://www.chinanews.com.cn/rss/society.xml"),
    NewsSource("中新网财经", "China Deep Read", "https://www.chinanews.com.cn/rss/finance.xml"),
    NewsSource("人民网时政", "China Deep Read", "http://www.people.com.cn/rss/politics.xml"),
    NewsSource("人民网社会", "China Deep Read", "http://www.people.com.cn/rss/society.xml"),
    NewsSource("人民网财经", "China Deep Read", "http://www.people.com.cn/rss/finance.xml"),
    NewsSource(
        "Google新闻中国民生",
        "China Deep Read",
        "https://news.google.com/rss/search?q=%E4%B8%AD%E5%9B%BD%20%E6%B0%91%E7%94%9F%20OR%20%E5%B0%B1%E4%B8%9A%20OR%20%E6%88%BF%E5%9C%B0%E4%BA%A7%20OR%20%E5%8C%BB%E4%BF%9D%20OR%20%E6%95%99%E8%82%B2&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    ),
]
