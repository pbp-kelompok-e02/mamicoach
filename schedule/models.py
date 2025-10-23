from django.db import models
from django.contrib.auth.models import User

class ScheduleSlot(models.Model):
    coach = models.ForeignKey('user_profile.CoachProfile', on_delete=models.CASCADE, related_name='schedule_slots')
    date = models.DateField(help_text="Specific date for this schedule")
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        unique_together = ['coach', 'date', 'start_time']
    
    def clean(self):
        from django.core.exceptions import ValidationError
        from datetime import date as dt_date
        
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
        
        if self.date < dt_date.today():
            raise ValidationError('Cannot create schedule for past dates')
    
    def __str__(self):
        return f"{self.coach.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"