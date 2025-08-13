from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.signals import user_logged_in

# Import models
from .models import Profile
from news.models import Comment, ArticleFeedback # Import Comment and new ArticleFeedback model

# Import forms
from .forms import UserUpdateForm, ProfileUpdateForm, UserRegisterForm, CustomAuthenticationForm


def register_view(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}! You can now log in.')
            return redirect('users:login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('news:homepage')
    else:
        form = CustomAuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('news:homepage')

@login_required
def profile_view(request, username):
    # This is the main profile view that displays the profile page
    profile_user = get_object_or_404(User, username=username)
    user_comments = Comment.objects.filter(user=profile_user).order_by('-created_at')[:10]
    
    # Calculate feedback counts for the user whose profile is being viewed
    useful_count = ArticleFeedback.objects.filter(user=profile_user, is_useful=True).count()
    not_useful_count = ArticleFeedback.objects.filter(user=profile_user, is_useful=False).count()

    context = {
        'profile_user': profile_user,
        'user_comments': user_comments,
        'useful_count': useful_count,
        'not_useful_count': not_useful_count,
    }
    return render(request, 'users/profile.html', context)

@login_required
def edit_profile_view(request):
    # This view handles the form for editing a profile
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('users:profile', username=request.user.username)
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'users/profile_edit.html', context)

@login_required
def useful_articles_list(request):
    # Displays a list of articles the logged-in user marked as 'Useful'
    useful_feedback = ArticleFeedback.objects.filter(user=request.user, is_useful=True)
    articles = [feedback.article for feedback in useful_feedback]
    context = {
        'articles': articles,
        'feedback_type': 'Useful'
    }
    return render(request, 'users/feedback_articles_list.html', context)

@login_required
def not_useful_articles_list(request):
    # Displays a list of articles the logged-in user marked as 'Not Useful'
    not_useful_feedback = ArticleFeedback.objects.filter(user=request.user, is_useful=False)
    articles = [feedback.article for feedback in not_useful_feedback]
    context = {
        'articles': articles,
        'feedback_type': 'Not Useful'
    }
    return render(request, 'users/feedback_articles_list.html', context)

@receiver(user_logged_in)
def update_streak(sender, request, user, **kwargs):
    # This function updates the user's login streak
    profile, created = Profile.objects.get_or_create(user=user)
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    if profile.last_login_date == yesterday:
        profile.streak_count += 1
    elif profile.last_login_date != today:
        profile.streak_count = 1
        
    profile.last_login_date = today
    profile.save()