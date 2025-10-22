from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CoachProfile, Certification


SPORT_CHOICES = [
    ('Fitness', 'Fitness'),
    ('Yoga', 'Yoga'),
    ('Pilates', 'Pilates'),
    ('Bodybuilding', 'Bodybuilding'),
    ('Weightlifting', 'Weightlifting'),
    ('CrossFit', 'CrossFit'),
    ('Running', 'Running'),
    ('Marathon', 'Marathon'),
    ('Swimming', 'Swimming'),
    ('Cycling', 'Cycling'),
    ('Boxing', 'Boxing'),
    ('Kickboxing', 'Kickboxing'),
    ('Muay Thai', 'Muay Thai'),
    ('Martial Arts', 'Martial Arts'),
    ('Basketball', 'Basketball'),
    ('Football', 'Football'),
    ('Soccer', 'Soccer'),
    ('Tennis', 'Tennis'),
    ('Badminton', 'Badminton'),
    ('Volleyball', 'Volleyball'),
    ('Baseball', 'Baseball'),
    ('Golf', 'Golf'),
    ('Gymnastics', 'Gymnastics'),
    ('Dance', 'Dance'),
    ('Zumba', 'Zumba'),
    ('Aerobics', 'Aerobics'),
    ('HIIT', 'HIIT (High-Intensity Interval Training)'),
    ('Calisthenics', 'Calisthenics'),
    ('Nutrition', 'Nutrition'),
    ('Sports Nutrition', 'Sports Nutrition'),
    ('Weight Loss', 'Weight Loss'),
    ('Strength Training', 'Strength Training'),
    ('Functional Training', 'Functional Training'),
    ('Personal Training', 'Personal Training'),
    ('Athletic Performance', 'Athletic Performance'),
    ('Rehabilitation', 'Rehabilitation'),
    ('Mobility', 'Mobility'),
    ('Flexibility', 'Flexibility'),
    ('Meditation', 'Meditation'),
    ('Wellness', 'Wellness'),
]


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