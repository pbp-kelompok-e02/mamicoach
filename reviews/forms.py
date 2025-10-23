from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'content', 'is_anonymous']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'type': 'hidden',
                'id': 'rating-value',
                'min': '1',
                'max': '5',
                'required': 'required',
            }),
            'content': forms.Textarea(attrs={
                'id': 'comment',
                'rows': '6',
                'placeholder': 'Ceritakan pengalaman Anda mengikuti kelas ini. Bagaimana cara mengajar coach? Apakah materi mudah dipahami? Apa yang bisa diperbaiki?',
                'class': 'w-full rounded-xl border border-neutral-200 bg-neutral-50 px-4 py-4 text-neutral-700 placeholder-neutral-400 transition focus:border-primary focus:bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 sm:text-base',
                'required': 'required',
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'id': 'is_anonymous_input',
                'class': 'absolute inset-0 h-full w-full cursor-pointer appearance-none rounded-md bg-[#E6E6E6] transition duration-150 focus:outline-none focus:ring-2 focus:ring-primary/40 focus:ring-offset-2',
            }),
        }
        labels = {
            'rating': 'Rating',
            'content': 'Share your thoughts',
            'is_anonymous': 'Post anonymously',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        rating = cleaned_data.get('rating')
        content = cleaned_data.get('content')
        
        # Validate rating
        if not rating:
            self.add_error('rating', 'Please select a rating (1-5 stars).')
        elif rating < 1 or rating > 5:
            self.add_error('rating', 'Rating must be between 1 and 5.')
        
        # Validate content
        if not content:
            self.add_error('content', 'Please write your review (at least some text).')
        elif len(content.strip()) < 10:
            self.add_error('content', 'Your review must be at least 10 characters long.')
        elif len(content.strip()) > 5000:
            self.add_error('content', 'Your review cannot exceed 5000 characters.')
        
        return cleaned_data
