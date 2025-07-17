from django.db import models

# Create your models here.
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)

    def str(self):
        return self.name

class Article(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.CharField(max_length=100)
    published_date = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)

    def str(self):
        return self.title

class UserPreference(models.Model):
    user_id = models.IntegerField()  # Later can be a ForeignKey to User model
    preferred_categories = models.ManyToManyField(Category)

class ReadingHistory(models.Model):
    user_id = models.IntegerField()  # Later can be a ForeignKey to User model
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    read_on = models.DateTimeField(auto_now_add=True)