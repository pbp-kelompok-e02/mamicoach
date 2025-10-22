from django.forms import ModelForm
from .models import CoachProfile

class CoachForm(ModelForm):
    class Meta:
        model = CoachProfile
        fields = ['bio', 'expertise', 'experience_years', 'image_url']