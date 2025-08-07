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
import logging
import requests
import time

logger = logging.getLogger(__name__)

def clean_html(raw_html):
    return BeautifulSoup(raw_html, "html.parser").get_text()

def clean_text_for_speech(text):
    """Clean text to improve speech synthesis."""
    if not text:
        return ""
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s,.!?\'"]', '', text)
    return text.strip()

def get_full_article_text(url):
    try:
        article = NewsArticle(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        logger.error(f"Error fetching article with newspaper3k from {url}: {e}")
        return ""

def fetch_full_article_content_fallback(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        for tag in ['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']:
            for element in soup.find_all(tag):
                element.decompose()

        content_blocks = []
        selectors = [
            '[data-component="text-block"]',
            '.ssrcss-1q0x1qg-Paragraph',
            '.story-body__inner p',
            '.zn-body__paragraph',
            '.el__leafmedia--sourced-paragraph',
            '.StandardArticleBody_body p',
            'article p',
            '.article-content p',
            '.entry-content p',
            '.post-content p',
            'p'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if len(elements) >= 3:
                for el in elements:
                    text = el.get_text(strip=True)
                    if len(text) > 40:
                        content_blocks.append(text)
                if content_blocks:
                    break

        full_content = '\n\n'.join(content_blocks[:12])
        full_content = clean_html(full_content)
        return full_content if len(full_content) > 200 else None

    except Exception as e:
        logger.error(f"Fallback full content fetch failed for {url}: {e}")
        return None

def generate_summary(text, sentence_limit=3):
    try:
        text = clean_html(text)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 25]

        if not sentences:
            return text[:300] + "..." if len(text) > 300 else text

        if len(sentences) <= sentence_limit:
            return '. '.join(sentences) + '.'

        important_keywords = [
            'announced', 'revealed', 'confirmed', 'reported', 'said', 'according',
            'new', 'first', 'major', 'significant', 'important', 'breaking',
            'today', 'yesterday', 'will', 'plans', 'expected', 'launched'
        ]

        scored_sentences = []
        for i, sentence in enumerate(sentences):
            score = 0
            s_lower = sentence.lower()

            for kw in important_keywords:
                if kw in s_lower:
                    score += 2

            if 60 <= len(sentence) <= 150:
                score += 3
            elif 30 <= len(sentence) <= 200:
                score += 1

            if i == 0:
                score += 4
            elif i < 3:
                score += 3
            elif i < 6:
                score += 1

            if re.search(r'\d+', sentence):
                score += 1

            if '"' in sentence or "'" in sentence:
                score += 2

            scored_sentences.append((sentence, score, i))

        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = scored_sentences[:sentence_limit]
        top_sentences.sort(key=lambda x: x[2])

        summary = '. '.join([s[0] for s in top_sentences])
        if summary and not summary.endswith('.'):
            summary += '.'

        return summary
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return text[:300] + "..."

def generate_audio_summary(text, article_id):
    try:
        if not text:
            logger.warning(f"No summary text for audio generation for article {article_id}")
            return None

        cleaned_text = clean_text_for_speech(text)
        if not cleaned_text:
            logger.warning(f"Summary too short after cleaning for article {article_id}")
            return None

        tts = gTTS(text=cleaned_text, lang='en', slow=False)
        filename = f"summary_{article_id}.mp3"
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'news_audio')
        os.makedirs(audio_dir, exist_ok=True)
        filepath = os.path.join(audio_dir, filename)

        tts.save(filepath)
        logger.info(f"Audio saved for article {article_id} at {filepath}")
        return os.path.join(settings.MEDIA_URL, 'news_audio', filename)
    except Exception as e:
        logger.error(f"Audio generation failed for article {article_id}: {e}")
        return None

def create_categories():
    categories = {}
    category_data = [
        ('technology', 'Technology', 'Latest technology news and innovations'),
        ('world', 'World', 'Global news and current events'),
        ('business', 'Business', 'Business and economic news'),
        ('science', 'Science', 'Science and research news'),
        ('health', 'Health', 'Health and medical news'),
        ('sports', 'Sports', 'Sports news and updates'),
    ]
    for key, name, desc in category_data:
        # THIS IS THE FIX: Removed the 'defaults' dictionary that was causing the error.
        category, _ = Category.objects.get_or_create(name=name)
        categories[key] = category
    return categories

RSS_FEEDS = {
    "Technology": "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "World": "https://feeds.bbci.co.uk/news/world/rss.xml",
    "Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Science": "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "Health": "https://feeds.bbci.co.uk/news/health/rss.xml",
}

def fetch_articles():
    categories = create_categories()
    new_articles = []

    for category_name, feed_url in RSS_FEEDS.items():
        category = categories.get(category_name.lower(), None)
        if not category:
            logger.warning(f"No category found for {category_name}, skipping feed.")
            continue

        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:5]:
            try:
                # Assuming your Article model has a 'url' field that should be unique
                if Article.objects.filter(url=entry.link).exists():
                    continue

                published_at = timezone.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6], tzinfo=pytz.UTC)

                full_content = get_full_article_text(entry.link)
                if not full_content or len(full_content) < 300:
                    fallback_content = fetch_full_article_content_fallback(entry.link)
                    if fallback_content and len(fallback_content) > len(full_content or ''):
                        full_content = fallback_content

                if not full_content or len(full_content) < 100:
                    logger.info(f"Skipping article due to short content: {entry.link}")
                    continue

                summary = generate_summary(full_content)

                article = Article.objects.create(
                    title=clean_html(entry.title)[:200],
                    author=entry.get("author", "Unknown"),
                    content=full_content,
                    url=entry.link,  # Make sure this field name matches your model
                    source=category_name, # Use the category name as the source
                    published_at=published_at,
                    summary=summary,
                )
                article.category.add(category) # Add the category relationship

                audio_url = generate_audio_summary(summary, article.id)
                if audio_url:
                    # Correctly format the relative path for the FileField
                    relative_path = os.path.join('news_audio', f"summary_{article.id}.mp3")
                    article.audio_file.name = relative_path
                    article.save()

                new_articles.append(article)

            except Exception as e:
                logger.error(f"Error processing article from feed {feed_url} ({entry.link}): {e}")
                continue

            time.sleep(1)

    logger.info(f"Fetched and created {len(new_articles)} new articles")
    return new_articles