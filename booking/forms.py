from django import forms
from .models import Booking
from schedule.models import ScheduleSlot
from courses_and_coach.models import Course

class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ['course', 'schedule', 'date']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'course': forms.Select(attrs={
                'class': 'form-control'
            }),
            'schedule': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'course': 'Pilih Kelas',
            'schedule': 'Pilih Jadwal',
            'date': 'Tanggal',
        }
    
    def __init__(self, *args, coach=None, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter schedule dan course berdasarkan coach
        if coach:
            self.fields['schedule'].queryset = ScheduleSlot.objects.filter(
                coach=coach, 
                is_available=True
            ).order_by('day_of_week', 'start_time')
            
            self.fields['course'].queryset = Course.objects.filter(
                coach=coach
            )
        else:
            # Jika tidak ada coach, tampilkan semua yang available
            self.fields['schedule'].queryset = ScheduleSlot.objects.filter(
                is_available=True
            ).order_by('day_of_week', 'start_time')
            
            self.fields['course'].queryset = Course.objects.all()
    
    def clean(self):
        cleaned_data = super().clean()
        schedule = cleaned_data.get('schedule')
        course = cleaned_data.get('course')
        date = cleaned_data.get('date')
        
        # Validasi bahwa schedule dan course dari coach yang sama
        if schedule and course:
            if schedule.coach != course.coach:
                raise forms.ValidationError(
                    'Schedule dan course harus dari coach yang sama'
                )
        
        # Validasi tanggal tidak di masa lalu
        if date:
            from datetime import date as dt
            if date < dt.today():
                raise forms.ValidationError(
                    'Tanggal booking tidak boleh di masa lalu'
                )
        
        return cleaned_data


class BookingFilterForm(forms.Form):
    """Form untuk filter booking berdasarkan hari dan coach"""
    DAYS_OF_WEEK = [
        ('', 'Semua Hari'),
        ('Monday', 'Senin'),
        ('Tuesday', 'Selasa'),
        ('Wednesday', 'Rabu'),
        ('Thursday', 'Kamis'),
        ('Friday', 'Jumat'),
        ('Saturday', 'Sabtu'),
        ('Sunday', 'Minggu'),
    ]
    
    STATUS_CHOICES = [
        ('', 'Semua Status'),
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    day = forms.ChoiceField(
        choices=DAYS_OF_WEEK,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    coach = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label='Semua Coach'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from user_profile.models import CoachProfile
        self.fields['coach'].queryset = CoachProfile.objects.all()