# models.py
from django.utils import timezone  
from django.db import models
from django.contrib.auth.models import User

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
        from .models import SummaryFeedback
        return {
            "useful": SummaryFeedback.objects.filter(article=self, useful=True).count(),
            "not_useful": SummaryFeedback.objects.filter(article=self, useful=False).count()
        }
    