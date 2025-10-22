from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CoachProfile, Certification


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
    expertise = forms.CharField(
        max_length=500, 
        required=True,
        help_text="Enter expertise areas separated by commas (e.g., Fitness, Yoga, Nutrition)"
    )
    image_url = forms.CharField(max_length=255, required=False)
    
    # Fields untuk certifications (multiple, separated by newline)
    certification_names = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Enter certification names, one per line"
    )
    certification_urls = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Enter certification file URLs, one per line (must match the order of names)"
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'password1', 'password2', 'bio', 'expertise', 'image_url', 'certification_names', 'certification_urls']
    
    def clean_expertise(self):
        """Convert comma-separated string to list"""
        expertise_str = self.cleaned_data.get('expertise', '')
        # Split by comma and strip whitespace
        expertise_list = [item.strip() for item in expertise_str.split(',') if item.strip()]
        if not expertise_list:
            raise forms.ValidationError('Please enter at least one expertise area.')
        return expertise_list
    
    def clean(self):
        """Validate that certification names and URLs match in count"""
        cleaned_data = super().clean()
        cert_names = cleaned_data.get('certification_names', '')
        cert_urls = cleaned_data.get('certification_urls', '')
        
        if cert_names or cert_urls:
            # Split by newline and filter empty lines
            names_list = [name.strip() for name in cert_names.split('\n') if name.strip()]
            urls_list = [url.strip() for url in cert_urls.split('\n') if url.strip()]
            
            if len(names_list) != len(urls_list):
                raise forms.ValidationError(
                    'Number of certification names and URLs must match. '
                    f'Found {len(names_list)} names and {len(urls_list)} URLs.'
                )
            
            cleaned_data['certification_names_list'] = names_list
            cleaned_data['certification_urls_list'] = urls_list
        else:
            cleaned_data['certification_names_list'] = []
            cleaned_data['certification_urls_list'] = []
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            # Create coach profile
            coach_profile = CoachProfile.objects.create(
                user=user,
                bio=self.cleaned_data['bio'],
                expertise=self.cleaned_data['expertise'],
                image_url=self.cleaned_data.get('image_url', '')
            )
            
            # Create certifications if provided
            names_list = self.cleaned_data.get('certification_names_list', [])
            urls_list = self.cleaned_data.get('certification_urls_list', [])
            
            for name, url in zip(names_list, urls_list):
                Certification.objects.create(
                    coach=coach_profile,
                    certificate_name=name,
                    file_url=url,
                    verified=False
                )
        
        return user