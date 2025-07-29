import re
import feedparser
from bs4 import BeautifulSoup
from django.utils import timezone
from news.models import Article, Category
from datetime import datetime
import pytz
import os
from gtts import gTTS
from django.conf import settings
from newspaper import Article as NewsArticle
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
import logging

logger = logging.getLogger(__name__)


def clean_html(raw_html):
    return BeautifulSoup(raw_html, "html.parser").get_text()

def get_full_article_text(url):
    try:
        article = NewsArticle(url)
        article.download()
        article.parse()
        return article.text
    except:
        return ""

def generate_summary(text, sentence_limit=3):
    try:
        parser = PlaintextParser.from_string(text, Tokenizer("english"))
        summarizer = TextRankSummarizer()
        summary = summarizer(parser.document, sentence_limit)
        return " ".join(str(sentence) for sentence in summary)
    except:
        return text[:300] + "..."

def generate_audio_summary(text, article_id):
    if not text:
        logger.warning(f"No text for article {article_id}")
        return None

    filename = f"summary_{article_id}.mp3"
    audio_dir = os.path.join(settings.MEDIA_ROOT, 'news_audio')
    os.makedirs(audio_dir, exist_ok=True)
    filepath = os.path.join(audio_dir, filename)

    try:
        tts = gTTS(text=text, lang='en')
        tts.save(filepath)
        logger.info(f"Audio for article {article_id} saved at {filepath}")
        return os.path.join(settings.MEDIA_URL, 'news_audio', filename)
    except Exception as e:
        logger.error(f"Audio generation failed for article {article_id}: {e}")
        return None

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
                continue

            title = entry.title
            author = entry.get("author", "Unknown")
            published = entry.get("published", timezone.now().isoformat())
            try:
                published_at = datetime(*entry.published_parsed[:6], tzinfo=pytz.UTC)
            except:
                published_at = timezone.now()

            full_content = get_full_article_text(entry.link)
            summary = generate_summary(full_content)

            article = Article.objects.create(
                title=title,
                author=author,
                content=full_content,
                url=entry.link,
                source=source,
                published_at=published_at,
                summary=summary,
            )

            category_name = source
            category, _ = Category.objects.get_or_create(name=category_name)
            article.category.add(category)

            # ✅ Generate audio
            audio_url = generate_audio_summary(summary, article.id)
            if audio_url:
                relative_path = os.path.relpath(audio_url, settings.MEDIA_URL)
                article.audio_file.name = relative_path
                article.save()

            new_articles.append(article)
    return new_articles