from django.contrib import admin
from .models import UserProfile, CoachProfile, Certification, AdminVerification

# Register your models here.
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

class CoachProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rating', 'verified', 'created_at')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    list_filter = ('verified', 'rating')

class CertificationAdmin(admin.ModelAdmin):
    list_display = ('coach', 'certificate_name', 'status', 'uploaded_at')
    list_filter = ('status',)
    search_fields = ('coach__user__username', 'certificate_name')

class AdminVerificationAdmin(admin.ModelAdmin):
    list_display = ('coach', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('coach__user__username',)
