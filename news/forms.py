from django import forms
from .models import UserPreference
from .models import SummaryFeedback

class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ['preferred_categories']
        widgets = {
            'preferred_categories': forms.CheckboxSelectMultiple,
        }

class SummaryFeedbackForm(forms.ModelForm):
    class Meta:
        model = SummaryFeedback
        fields = ['useful']
        widgets = {
            'useful': forms.RadioSelect(choices=[(True, "Useful"), (False, "Not Useful")]),
        }