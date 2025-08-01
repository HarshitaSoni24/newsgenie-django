from django import forms
from .models import UserPreference, SummaryFeedback, Comment # Import Comment

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

# NEW FORM: CommentForm
class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your comment here...'}),
        }
        labels = {
            'content': '' # No label for content field, use placeholder instead
        }