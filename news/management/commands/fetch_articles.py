from django.core.management.base import BaseCommand
from news.utils.scraper import fetch_articles # This is the most important import
import logging

# This sets up logging so you can see messages in your terminal
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Fetches news articles, generates summaries and audio, and saves them to the database.'

    def handle(self, *args, **options):
        """This is the main function that runs when you call the command."""
        
        self.stdout.write(self.style.SUCCESS("Starting the news fetching process..."))
        
        try:
            # Here, we call the main function from your scraper.py file
            new_articles = fetch_articles()
            
            success_message = f"Successfully fetched and created {len(new_articles)} new articles."
            self.stdout.write(self.style.SUCCESS(success_message))
            
        except Exception as e:
            # If something goes wrong, this will print a helpful error message
            logger.error(f"The script failed unexpectedly: {e}")
            self.stderr.write(self.style.ERROR("The script failed. Check the logs for more details."))