from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CoachProfile, Certification


def get_sport_choices():
    from courses_and_coach.models import Category
    categories = Category.objects.all().order_by('name')
    return [(cat.name, cat.name) for cat in categories]


class TraineeRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password1', 'password2']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].error_messages = {
            'unique': 'This username is already taken. Please choose a different one.',
        }


class CoachRegistrationForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    bio = forms.CharField(widget=forms.Textarea, required=True)
    image_url = forms.CharField(max_length=255, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password1', 'password2', 'bio', 'image_url']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].error_messages = {
            'unique': 'This username is already taken. Please choose a different one.',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user