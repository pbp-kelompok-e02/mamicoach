from django import forms
from .models import CoachProfile

class CoachProfileForm(forms.ModelForm):
    class Meta:
        model = CoachProfile
        fields = ['bio', 'expertise', 'experience_years', 'image_url']
        widgets = {
            'bio': forms.Textarea(attrs={
                'placeholder': 'Tell us about yourself...',
                'rows': 4
            }),
            'expertise': forms.TextInput(attrs={
                'placeholder': 'E.g., Fitness, Yoga, Business Coaching'
            }),
            'experience_years': forms.NumberInput(attrs={
                'placeholder': 'Years of experience',
                'min': 0
            }),
            'image_url': forms.URLInput(attrs={
                'placeholder': 'Profile image URL (optional)'
            })
        }
        labels = {
            'bio': 'Bio',
            'expertise': 'Area of Expertise',
            'experience_years': 'Years of Experience',
            'image_url': 'Profile Image URL'
        }