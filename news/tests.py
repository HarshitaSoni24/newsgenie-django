from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from news.models import Article, Category, UserPreference
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
import os
from unittest.mock import patch, MagicMock

User = get_user_model()

class ArticleModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Technology')

    def test_create_article_with_category(self):
        """
        Test that an article can be created and correctly associated with a category.
        """
        article = Article.objects.create(
            title='Test Article',
            source='Test Source',
            content='This is a test content.',
            approved=False,
            summary='This is a test summary.',
            url='http://test.com/article1',
            published_at=timezone.now()
        )
        article.category.add(self.category)
        self.assertEqual(article.category.count(), 1)
        self.assertIn(self.category, article.category.all())

    def test_approved_status_method(self):
        """
        Test the custom approved_status method to ensure it returns the correct boolean.
        """
        approved_article = Article.objects.create(
            title='Approved Article',
            source='Approved Source',
            content='Approved content.',
            approved=True,
            url='http://test.com/approved_article',
            published_at=timezone.now()
        )
        unapproved_article = Article.objects.create(
            title='Unapproved Article',
            source='Unapproved Source',
            content='Unapproved content.',
            approved=False,
            url='http://test.com/unapproved_article',
            published_at=timezone.now()
        )
        self.assertTrue(approved_article.approved_status())
        self.assertFalse(unapproved_article.approved_status())

    def test_article_fields_are_correct(self):
        """
        Test that the fields of an article contain the data you put in.
        """
        article = Article.objects.create(
            title='Another Test Title',
            source='Another Test Source',
            content='Another test content.',
            summary='Another test summary.',
            url='http://test.com/another_test',
            published_at=timezone.now()
        )
        self.assertEqual(article.title, 'Another Test Title')
        self.assertEqual(article.source, 'Another Test Source')
        self.assertEqual(article.content, 'Another test content.')
        self.assertEqual(article.summary, 'Another test summary.')


class UserPreferenceModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='prefuser', password='password')
        self.category1 = Category.objects.create(name='Sports')
        self.category2 = Category.objects.create(name='Politics')
        self.category3 = Category.objects.create(name='Science')

    def test_user_preference_categories(self):
        """
        Test that categories are correctly saved to a user's preference.
        """
        preference = UserPreference.objects.create(user=self.user)
        preference.preferred_categories.add(self.category1, self.category2)
        
        self.assertEqual(preference.preferred_categories.count(), 2)
        self.assertIn(self.category1, preference.preferred_categories.all())
        self.assertIn(self.category2, preference.preferred_categories.all())
        self.assertNotIn(self.category3, preference.preferred_categories.all())

class IntegrationTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='admin', password='password')
        self.approved_article = Article.objects.create(
            title='Approved Article',
            source='Approved Source',
            content='Content for approved article.',
            approved=True,
            url='http://test.com/approved',
            published_at=timezone.now()
        )
        self.unapproved_article = Article.objects.create(
            title='Unapproved Article',
            source='Unapproved Source',
            content='Content for unapproved article.',
            approved=False,
            url='http://test.com/unapproved',
            published_at=timezone.now()
        )
        self.category1 = Category.objects.create(name='Technology')
        self.client.login(username='admin', password='password')

    @patch('news.management.commands.scrape_news.Command.handle')
    def test_scrape_news_command(self, mock_handle):
        """
        Test that the scrape_news command creates new articles with approved=False.
        """
        # Mock the fetch_articles utility function to return a list of new articles
        new_articles = [
            Article(title='Scraped Article 1', source='Scraper Source', content='...', approved=False, url='http://test.com/scraped_1', published_at=timezone.now()),
            Article(title='Scraped Article 2', source='Scraper Source', content='...', approved=False, url='http://test.com/scraped_2', published_at=timezone.now()),
        ]
        mock_handle.return_value = None # Mock the return value of the handle method
        
        initial_article_count = Article.objects.count()
        call_command('scrape_news') # Corrected: The management command name is scrape_news
        
        self.assertGreater(Article.objects.count(), initial_article_count)
        
        scraped_article_1 = Article.objects.get(title='Scraped Article 1')
        self.assertFalse(scraped_article_1.approved)
        scraped_article_2 = Article.objects.get(title='Scraped Article 2')
        self.assertFalse(scraped_article_2.approved)

    @patch('news.views.GenerateAudioAPIView.post')
    def test_audio_generation_api(self, mock_post):
        """
        Simulate a POST request to generate_audio_ajax endpoint and check the response.
        """
        mock_post.return_value = MagicMock(
            status_code=200, 
            json=lambda: {'audio_url': 'http://test.com/media/news_audio/test_audio.mp3'}
        )
        
        article_with_content = Article.objects.create(
            title='Audio Test Article',
            content='This is a short test summary for audio generation.',
            approved=True,
            url='http://test.com/audio',
            published_at=timezone.now()
        )
        url = reverse('api_generate_audio', kwargs={'pk': article_with_content.id})
        
        response = self.client.post(url, format='json')
        
        self.assertEqual(response.status_code, 200)
        
        self.assertIn('audio_url', response.json())
        
        self.assertIn('test_audio.mp3', response.json()['audio_url'])

    def test_approval_workflow(self):
        """
        Test that unapproved articles do not appear in the main article list view.
        """
        response = self.client.get(reverse('news:article_list'))
        
        self.assertNotIn(self.unapproved_article.title.encode(), response.content)
        
        self.assertIn(self.approved_article.title.encode(), response.content)