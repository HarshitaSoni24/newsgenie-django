from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path('', views.homepage, name="homepage"), # MODIFIED: Homepage is now the root
    path('articles/', views.article_list, name="article_list"), # MODIFIED: Articles page moved to /articles/
    path('article/<int:pk>/', views.article_detail, name="detail"),
    
     # NEW FEATURE: URL for generating the word cloud image
    path('article/<int:pk>/wordcloud/', views.generate_word_cloud_view, name="word_cloud"),

    path('article/<int:pk>/generate-summary/', views.generate_summary_view, name="generate_summary"),
    path('article/<int:pk>/generate-audio/', views.generate_audio_view, name="generate_audio"),
    path('article/<int:pk>/like-toggle/', views.toggle_article_like, name="like_toggle"),
    path('article/<int:pk>/bookmark-toggle/', views.toggle_article_bookmark, name="bookmark_toggle"),
    path('track-metrics/', views.track_article_metrics, name="track_metrics"),
    path('bookmarks/', views.bookmark_list, name="bookmarks"),
    path('preferences/', views.preference_view, name="preferences"),
    path('recommendations/', views.personalized_recommendations, name="recommendations"),
    path('history/', views.reading_history, name="history"),
    path('scraper/', views.run_scraper_view, name="scraper"),
]