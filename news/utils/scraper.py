#scaper.py
import re
import feedparser
from bs4 import BeautifulSoup
from django.utils import timezone
from news.models import Article, Category
from datetime import datetime
import pytz

def clean_html(raw_html):
    return BeautifulSoup(raw_html, "html.parser").get_text()

def enhanced_summary(text, sentence_limit=2):
    sentences = re.split(r'(?<=[.!?]) +', text)
    important_sentences = [s for s in sentences if any(q in s.lower() for q in ['what', 'why', 'how'])]
    selected = important_sentences[:sentence_limit]
    if len(selected) < sentence_limit:
        selected += sentences[:sentence_limit - len(selected)]
    return ' '.join(selected)

RSS_FEEDS = {
    "BBC": "http://feeds.bbci.co.uk/news/rss.xml",
    "CNN": "http://rss.cnn.com/rss/edition.rss",
    "Reuters": "http://feeds.reuters.com/reuters/topNews"
}

def fetch_articles():
    new_articles = []
    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if Article.objects.filter(url=entry.link).exists():
                continue  # Skip duplicates

            title = entry.title
            content = clean_html(entry.get("summary", ""))
            author = entry.get("author", "Unknown")
            published = entry.get("published", timezone.now().isoformat())
            try:
                published_at = datetime(*entry.published_parsed[:6], tzinfo=pytz.UTC)
            except:
                published_at = timezone.now()

            article = Article.objects.create(
                title=title,
                author=author,
                content=content,
                url=entry.link,
                source=source,
                published_at=published_at,
                summary=enhanced_summary(content),
            )

            category_name = source
            category, _ = Category.objects.get_or_create(name=category_name)
            article.category.add(category)
            new_articles.append(article)
    return new_articles