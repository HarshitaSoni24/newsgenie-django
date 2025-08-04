# bytenews/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Ensure settings is imported
from django.conf.urls.static import static

# DRF IMPORTS
from rest_framework import routers
from news.views import ArticleViewSet, UserPreferenceViewSet, GenerateAudioAPIView


router = routers.DefaultRouter()
router.register(r'articles', ArticleViewSet)
router.register(r'preferences', UserPreferenceViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include('news.urls')), # Your existing web app URLs
    path('api/', include(router.urls)), # Your API URLs from router
    path('api/articles/<int:pk>/generate_audio/', GenerateAudioAPIView.as_view(), name='api_generate_audio'),
]

# Debug Toolbar URLs (from PDF, cite: 8)
if settings.DEBUG:
    import debug_toolbar # Import debug_toolbar only if DEBUG is True
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)), # Use __debug__ as per DRF docs
    ] + urlpatterns # Add debug toolbar paths first

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)