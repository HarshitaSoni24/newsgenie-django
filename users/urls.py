from django.urls import path
from .views import (
    register_view,
    login_view,
    logout_view,
    profile_view,
    edit_profile_view,
    useful_articles_list,
    not_useful_articles_list,
)

app_name = 'users'

urlpatterns = [
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # --- FIX: Specific paths must come BEFORE the general path ---
    path('profile/edit/', edit_profile_view, name='edit_profile'),
    path('profile/useful-articles/', useful_articles_list, name='useful-articles-list'),
    path('profile/not-useful-articles/', not_useful_articles_list, name='not-useful-articles-list'),

    # General path with a variable comes LAST
    path('profile/<str:username>/', profile_view, name='profile'),
]