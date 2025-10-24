from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Booking(models.Model):
    """
    Booking model - represents a user's booking for a course at a specific datetime.
    Uses start_datetime and end_datetime for precise time tracking.
    
    Status Flow:
    1. pending -> User creates booking, waiting for payment
    2. paid -> User completes payment, waiting for coach confirmation
    3. confirmed -> Coach accepts the booking
    4. done -> Session completed
    5. canceled -> Booking canceled (can happen at any stage)
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Payment'),
        ('paid', 'Paid'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('canceled', 'Canceled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    coach = models.ForeignKey('user_profile.CoachProfile', on_delete=models.CASCADE, related_name='coach_bookings')
    course = models.ForeignKey('courses_and_coach.Course', on_delete=models.CASCADE, related_name='course_bookings')
    
    # Keep old fields for migration compatibility
    schedule = models.ForeignKey('schedule.ScheduleSlot', on_delete=models.CASCADE, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    
    # New datetime fields
    start_datetime = models.DateTimeField(null=True, blank=True, help_text="Start date and time of the booking")
    end_datetime = models.DateTimeField(null=True, blank=True, help_text="End date and time of the booking")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['coach', 'start_datetime']),
            models.Index(fields=['coach', 'end_datetime']),
            models.Index(fields=['status']),
            models.Index(fields=['user']),
        ]
    
    def clean(self):
        if self.start_datetime and self.end_datetime:
            if self.end_datetime <= self.start_datetime:
                raise ValidationError('End datetime must be after start datetime')
            
            # Validate that coach owns the course
            if self.course and self.coach and self.course.coach != self.coach:
                raise ValidationError('Course must belong to the selected coach')
    
    def save(self, *args, **kwargs):
        # Only validate if we have the new datetime fields
        if self.start_datetime and self.end_datetime:
            self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.user.username} - {self.course.title} @ {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def date(self):
        """Return date portion of start_datetime for compatibility"""
        if self.start_datetime:
            return self.start_datetime.date()
        return self.date  # fallback to old date field
    
    @property 
    def start_time(self):
        """Return time portion of start_datetime"""
        if self.start_datetime:
            return self.start_datetime.time()
        return None
    
    @property
    def end_time(self):
        """Return time portion of end_datetime"""
        if self.end_datetime:
            return self.end_datetime.time()
        return None
