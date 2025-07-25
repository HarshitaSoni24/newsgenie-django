from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path('', views.article_list, name="article_list"),
    path('article/<int:pk>/', views.article_detail, name="detail"),
    path('preferences/', views.preference_view, name="preferences"),
    path('recommendations/', views.personalized_recommendations, name="recommendations"),
    path('history/', views.reading_history, name="history"),
    path('scraper/', views.run_scraper_view, name="scraper"),
]
