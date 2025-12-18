from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date as dt_date


class CoachAvailability(models.Model):
    """
    Coach availability model - represents time ranges when coach is available on a specific date.
    Multiple ranges can exist for the same coach+date combination.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    
    coach = models.ForeignKey(
        'user_profile.CoachProfile', 
        on_delete=models.CASCADE, 
        related_name='availabilities'
    )
    date = models.DateField(help_text="Specific date for this availability")
    start_time = models.TimeField(help_text="Start time of availability range")
    end_time = models.TimeField(help_text="End time of availability range")
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='active',
        help_text="Availability status - active or inactive"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['date', 'start_time']
        indexes = [
            models.Index(fields=['coach', 'date']),
            models.Index(fields=['date']),
        ]
        verbose_name_plural = "Coach Availabilities"
    
    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
        
        if self.date and self.date < dt_date.today():
            raise ValidationError('Cannot create availability for past dates')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.coach.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"


# Keep ScheduleSlot for backward compatibility if needed
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
        if self.end_time <= self.start_time:
            raise ValidationError('End time must be after start time')
        
        if self.date < dt_date.today():
            raise ValidationError('Cannot create schedule for past dates')
    
    def __str__(self):
        return f"{self.coach.user.get_full_name()} - {self.date} {self.start_time}-{self.end_time}"