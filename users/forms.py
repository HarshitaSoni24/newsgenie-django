from django import forms
from django.contrib.auth.models import User
from .models import Profile

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        # This now correctly includes all three fields
        fields = ['first_name', 'last_name', 'email']
        # This widget dictionary applies the styling class to each field
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'auth-input'}),
            'last_name': forms.TextInput(attrs={'class': 'auth-input'}),
            'email': forms.EmailInput(attrs={'class': 'auth-input'}),
        }

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio']
        widgets = {
            'bio': forms.Textarea(attrs={
                'class': 'auth-input', 
                'rows': 4, 
                'placeholder': 'Tell everyone a little about yourself...'
            }),
        }