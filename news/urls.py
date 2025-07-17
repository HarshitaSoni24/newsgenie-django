from django.urls import path
from .views import ArticleListView, ArticleDetailView

app_name = 'news'

urlpatterns = [
    path('', ArticleListView.as_view(), name='article_list'),
    path('article/<int:pk>/', ArticleDetailView.as_view(), name='detail'),
]
