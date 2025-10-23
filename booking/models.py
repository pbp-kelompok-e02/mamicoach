from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Create your models here.
class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coach = models.ForeignKey('user_profile.CoachProfile', on_delete=models.CASCADE)
    course = models.ForeignKey('courses_and_coach.Course', on_delete=models.CASCADE)
    schedule = models.ForeignKey('schedule.ScheduleSlot', on_delete=models.CASCADE)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['coach', 'schedule', 'date']  # Prevent double booking
    
    def clean(self):
        # Validasi bahwa schedule milik coach yang benar
        if self.schedule and self.coach and self.schedule.coach != self.coach:
            raise ValidationError('Schedule must belong to the selected coach')
        
        # Validasi bahwa schedule tersedia
        if self.schedule and not self.schedule.is_available:
            raise ValidationError('Selected schedule slot is not available')
    
    def __str__(self):
        return f"{self.user.username} - {self.coach.user.username} - {self.date}"