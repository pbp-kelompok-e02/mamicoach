from django.db import models
from django.contrib.auth.models import User

class CoachProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField()
    expertise = models.JSONField(default=list) 
    image_url = models.CharField(max_length=255)
    rating = models.FloatField(default=0.0)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AdminVerification(models.Model):
    coach = models.OneToOneField(CoachProfile, on_delete=models.CASCADE)
    certificate_url = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Certification(models.Model):
    coach = models.ForeignKey(CoachProfile, on_delete=models.CASCADE)
    certificate_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=255)
    verified = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)