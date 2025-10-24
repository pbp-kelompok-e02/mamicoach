from django.db import models
from django.contrib.auth.models import User


class AdminSettings(models.Model):
    """
    Global admin settings for the platform
    """
    key = models.CharField(max_length=255, unique=True, help_text="Setting key")
    value = models.TextField(help_text="Setting value (JSON, string, or number)")
    description = models.TextField(blank=True, help_text="Description of this setting")
    module = models.CharField(max_length=100, help_text="Module this setting belongs to (e.g., 'booking', 'payment', 'courses')")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['module', 'key']
        verbose_name = "Admin Setting"
        verbose_name_plural = "Admin Settings"
    
    def __str__(self):
        return f"{self.module}.{self.key}"


class AdminActivityLog(models.Model):
    """
    Log of admin actions for audit trail
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=100, help_text="Module where action was performed")
    description = models.TextField(help_text="Description of the action")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Admin Activity Log"
        verbose_name_plural = "Admin Activity Logs"
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['module', '-created_at']),
            models.Index(fields=['action', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.action} - {self.module} - {self.created_at}"
