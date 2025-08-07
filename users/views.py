from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.models import User # Import the User model
from news.models import Comment # Import the Comment model 
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import Profile
from django.contrib.auth.decorators import login_required # Add this import
from .forms import UserUpdateForm, ProfileUpdateForm # Add this import

# This is your original register function, renamed to match the URL config
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully! Please log in.")
            return redirect('users:login')
    else:
        form = UserCreationForm()
    return render(request, 'users/register.html', {'form': form})

# This is the standard login view
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('news:homepage')
    else:
        form = AuthenticationForm()
    return render(request, 'users/login.html', {'form': form})

# This is the standard logout view
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect('news:homepage')

# THIS IS THE FIX: This function runs every time a user logs in.
# It gets the user's profile, OR CREATES ONE if it doesn't exist.
# This fixes the crash for users who existed before the Profile model was made.
@receiver(user_logged_in)
def update_streak(sender, request, user, **kwargs):
    profile, created = Profile.objects.get_or_create(user=user)
    
    today = timezone.now().date()
    yesterday = today - timedelta(days=1)
    
    if profile.last_login_date == yesterday:
        profile.streak_count += 1
    elif profile.last_login_date == today:
        pass  # Do nothing if they already logged in today
    else:
        # If they missed a day or it's their first login, reset streak to 1
        profile.streak_count = 1
        
    profile.last_login_date = today
    profile.save()

def profile_view(request, username):
    profile_user = get_object_or_404(User, username=username)
    user_comments = Comment.objects.filter(user=profile_user, approved=True).order_by('-created_at')
    
    context = {
        'profile_user': profile_user,
        'user_comments': user_comments,
    }
    return render(request, 'users/profile.html', context)


@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('users:profile', username=request.user.username)
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    
    return render(request, 'users/profile_edit.html', context)