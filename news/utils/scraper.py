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
from django.conf import settings
from django.utils import timezone
from news.models import Article, Category
from django.core.files.base import ContentFile
import google.generativeai as genai

genai.configure(api_key=os.environ.get('YOUR API KEY'))

# --- The rest of your code starts here ---
logger = logging.getLogger(__name__)
# ...
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

# This is the NEW, improved function
from newspaper import Config # Make sure this import is at the top of your file

def get_full_article_text(url):
    try:
        # ADD THIS CONFIGURATION BLOCK
        config = Config()
        config.request_timeout = 10  # Set a 10-second timeout
        config.browser_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'

        # Pass the config to the Article object
        article = NewsArticle(url, config=config)
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

#
# ADD THIS NEW FUNCTION TO YOUR CODE
##
# REPLACE your old function with this new one
#
import google.api_core.exceptions

def get_summary_from_gemini(content):
    """
    Generates a summary using Gemini, with a retry mechanism for rate limiting.
    """
    if not content or len(content) < 200:
        logger.warning("Content too short for Gemini summary, skipping.")
        return "Summary not available."

    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    prompt = f"Please act as a news editor. Summarize the following article concisely in a neutral, professional tone. The summary should be about 6-7 sentences long:\n\n---\n\n{content}"

    # This loop will try up to 3 times if we hit a rate limit
    for attempt in range(3):
        try:
            # Attempt to generate the summary
            response = model.generate_content(prompt)
            logger.info("Successfully generated summary with Gemini.")
            return response.text
        
        except google.api_core.exceptions.ResourceExhausted as e:
            # THIS IS THE FIX: We catch the "Quota Exceeded" error
            wait_time = (attempt + 1) * 15  # Wait longer each time: 15s, 30s, 45s
            logger.warning(f"Rate limit hit. Waiting for {wait_time} seconds before retrying... (Attempt {attempt + 1}/3)")
            time.sleep(wait_time) # The script politely waits

        except Exception as e:
            # For any other error, we just log it and stop
            logger.error(f"A non-rate-limit Gemini error occurred: {e}")
            return "Summary could not be generated."

    # This message is returned if all 3 retry attempts fail
    logger.error("All retry attempts failed due to rate limiting.")
    return "Summary could not be generated due to API rate limits."
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
        ('entertainment', 'Entertainment', 'Movie, music, and celebrity news'),
        ('politics', 'Politics', 'Government news, policy, and elections'),
        ('lifestyle', 'Lifestyle', 'Fashion, food, travel, and wellness news'),
        ('environment', 'Environment', 'News on climate change and conservation'),
        ('education', 'Education', 'News about schools and educational trends'),
        ('gaming', 'Gaming', 'Video game news, reviews, and esports'),
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
    "Sports": "http://feeds.bbci.co.uk/sport/rss.xml",
    "Entertainment": "https://feeds.bbci.co.uk/news/entertainment/rss.xml",
    "Politics": "https://feeds.bbci.co.uk/news/politics/rss.xml",
    "Lifestyle": "https://feeds.bbci.co.uk/news/lifestyle/rss.xml",
    "Environment": "https://feeds.bbci.co.uk/news/environment/rss.xml",
    "Education": "https://feeds.bbci.co.uk/news/education/rss.xml",
    "Gaming": "https://feeds.bbci.co.uk/news/gaming/rss.xml",
}

#
# REPLACE your old function with this new, more robust version
#
def fetch_articles():
    categories = create_categories()
    new_articles = []

    # This loop now has its own error handling
    for category_name, feed_url in RSS_FEEDS.items():
        try: # <-- START of the new safety block for the whole category
            print(f"\n--- Checking category: {category_name} ---")
            category = categories.get(category_name.lower(), None)
            if not category:
                logger.warning(f"No category found for {category_name}, skipping feed.")
                continue

            feed = feedparser.parse(feed_url)
            
            # This inner loop processes each article within the category
            for entry in feed.entries[:7]: # We'll keep the limit low to respect APIs
                try:
                    if Article.objects.filter(url=entry.link).exists():
                        continue

                    published_at = timezone.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6], tzinfo=pytz.UTC)

                    full_content = get_full_article_text(entry.link)
                    if not full_content or len(full_content) < 200:
                        continue
                    
                    print(f"--> PROCESSING: '{entry.title[:50]}...'")
                    summary_text = get_summary_from_gemini(full_content)

                    article = Article.objects.create(
                        title=clean_html(entry.title)[:200],
                        author=entry.get("author", "Unknown"),
                        content=full_content,
                        url=entry.link,
                        source=category_name,
                        published_at=published_at,
                        summary=summary_text,
                        approved=True,
                    )
                    article.category.add(category)
                    
                    audio_url = generate_audio_summary(summary_text, article.id)
                    if audio_url:
                        relative_path = os.path.join('news_audio', f"summary_{article.id}.mp3")
                        article.audio_file.name = relative_path
                        article.save()

                    new_articles.append(article)
                    time.sleep(2) # A polite pause

                except Exception as e:
                    logger.error(f"Error on article '{entry.link}'. Moving to next article. Error: {e}")
                    continue # Safely move to the next article

        except Exception as e:
            # If the whole feed fails (e.g., bad URL), log it and move on
            logger.error(f"FATAL ERROR processing category '{category_name}'. Moving to next category. Error: {e}")
            continue # <-- END of the new safety block

    logger.info(f"Fetched and created {len(new_articles)} new articles across all categories.")
    return new_articles
