from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CoachProfile


class TraineeRegistrationForm(UserCreationForm):
    """Form untuk registrasi trainee dengan first_name dan last_name"""
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password1', 'password2']


class CoachRegistrationForm(UserCreationForm):
    """Form untuk registrasi coach yang sekaligus membuat user account"""
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    bio = forms.CharField(widget=forms.Textarea, required=True)
    expertise = forms.CharField(max_length=255, required=True)
    image_url = forms.CharField(max_length=255, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password1', 'password2', 'bio', 'expertise', 'image_url']
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            CoachProfile.objects.create(
                user=user,
                bio=self.cleaned_data['bio'],
                expertise=self.cleaned_data['expertise'],
                experience_years=0,
                image_url=self.cleaned_data.get('image_url', '')
            )
        return user