from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', include(('news.urls', 'news'), namespace='news')),
]
