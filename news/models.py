from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
import math 
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

    
class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=100, default="Unknown")
    content = models.TextField()
    url = models.URLField(unique=True)
    source = models.CharField(max_length=100)
    published_at = models.DateTimeField()
    summary = models.TextField(blank=True, null=True)
    category = models.ManyToManyField(Category, related_name='articles')
    approved = models.BooleanField(default=False)
    audio_file = models.FileField(upload_to='news_audio/', blank=True, null=True)

    # NEW FEATURE: Estimated Reading Time field
    reading_time = models.PositiveIntegerField(
        default=0, 
        help_text="Estimated reading time in minutes"
    )

    # NEW FEATURE: Automatically calculate reading time on save
    def save(self, *args, **kwargs):
        if self.content:
            word_count = len(self.content.split())
            # Assuming average of 225 words per minute
            time_to_read = math.ceil(word_count / 225)
            self.reading_time = max(1, time_to_read)
        else:
            self.reading_time = 0
        super().save(*args, **kwargs)


    @property
    def total_likes(self):
        return self.likes.count()

    @property
    def total_comments(self):
        return self.comments.count()


    def approved_status(self):
        return self.approved
    approved_status.boolean = True
    approved_status.short_description = "Approved"

    def __str__(self):
        return self.title

class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_categories = models.ManyToManyField(Category)

class ReadingHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    read_at = models.DateTimeField(default=timezone.now)

class SummaryFeedback(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    useful = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def feedback_counts(self):
        return {
            "useful": SummaryFeedback.objects.filter(article=self.article, useful=True).count(),
            "not_useful": SummaryFeedback.objects.filter(article=self.article, useful=False).count()
        }

class ArticleLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} likes {self.article.title}"

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'article')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} bookmarked {self.article.title}"

class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title[:30]}..."

# NEW MODEL: UserArticleMetrics (This was kept from your original file)
class UserArticleMetrics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    time_on_page = models.IntegerField(default=0, help_text="Time spent on page in seconds") # Track seconds
    scroll_depth = models.FloatField(default=0.0, help_text="Max scroll depth as a percentage (0.0 to 1.0)")
    last_tracked_at = models.DateTimeField(auto_now=True) # Automatically updates on save

    class Meta:
        unique_together = ('user', 'article') # One metrics record per user-article pair

    def __str__(self):
        return f"Metrics for {self.user.username} on {self.article.title[:30]}..."