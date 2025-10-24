from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    profile_image_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def image_url(self):
        if self.profile_image and hasattr(self.profile_image, 'url'):
            return self.profile_image.url
        if self.profile_image_url:
            return self.profile_image_url
        return f'https://ui-avatars.com/api/?name={self.user.get_full_name() or self.user.username}&background=35A753&color=ffffff'

    def __str__(self):
        return f"{self.user.username}'s Profile"

class CoachProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField()
    expertise = models.JSONField(default=list) 
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    profile_image_url = models.URLField(max_length=500, blank=True, null=True)
    rating = models.FloatField(default=0.0)
    rating_count = models.PositiveIntegerField(default=0)
    total_minutes_coached = models.PositiveIntegerField(default=0)
    balance = models.PositiveIntegerField(
        default=0,
        help_text="Price in the smallest currency unit (e.g., cents, rupiah)"
    )
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def image_url(self):
        if self.profile_image and hasattr(self.profile_image, 'url'):
            return self.profile_image.url
        if self.profile_image_url:
            return self.profile_image_url
        return f'https://ui-avatars.com/api/?name={self.user.get_full_name() or self.user.username}&background=35A753&color=ffffff'

    @property
    def total_hours_coached(self):
        """Return total hours coached from stored total_minutes_coached field"""
        return self.total_minutes_coached / 60
    
    @property
    def total_hours_coached_formatted(self):
        """Return formatted total hours coached (e.g., '242 jam' or '242.5 jam')"""
        hours = self.total_hours_coached
        if hours == int(hours):
            return f"{int(hours)} jam"
        else:
            return f"{hours:.1f} jam"

    @property
    def balance_formatted(self):
        """Return formatted balance with thousand separators (e.g., '1,000,000')"""
        return f"{self.balance:,}"

    def __str__(self):
        return f"{self.user.username} - Coach"


class AdminVerification(models.Model):
    coach = models.OneToOneField(CoachProfile, on_delete=models.CASCADE)
    certificate_url = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Certification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('declined', 'Declined'),
    ]
    
    coach = models.ForeignKey(CoachProfile, on_delete=models.CASCADE)
    certificate_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_at = models.DateTimeField(auto_now_add=True)