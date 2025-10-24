from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class AdminUser(models.Model):
    """
    Custom admin user model for admin panel authentication
    """
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)  # Hashed password
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Admin User"
        verbose_name_plural = "Admin Users"
    
    def __str__(self):
        return self.username
    
    def set_password(self, raw_password):
        """Hash and set the password"""
        self.password = make_password(raw_password)
    
    def check_password(self, raw_password):
        """Check if the provided password is correct"""
        return check_password(raw_password, self.password)


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
    updated_by = models.ForeignKey('AdminUser', on_delete=models.SET_NULL, null=True, blank=True)
    
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
    
    admin_user = models.ForeignKey('AdminUser', on_delete=models.CASCADE, related_name='admin_activities')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    module = models.CharField(max_length=100, help_text="Module where action was performed")
    description = models.TextField(help_text="Description of the action")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = "Admin Activity Log"
        verbose_name_plural = "Admin Activity Logs"
        indexes = [
            models.Index(fields=['admin_user', '-timestamp']),
            models.Index(fields=['module', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.admin_user.username} - {self.action} - {self.module} - {self.timestamp}"
