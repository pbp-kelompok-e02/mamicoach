from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'coach', 'course', 'date', 'status', 'created_at']
    list_filter = ['status', 'date', 'created_at']
    search_fields = ['user__username', 'coach__user__username']
    date_hierarchy = 'date'
    ordering = ['-created_at']
    
    # Actions untuk update status dari admin
    actions = ['mark_as_confirmed', 'mark_as_completed', 'mark_as_cancelled']
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f"{queryset.count()} booking(s) marked as Confirmed.")
    mark_as_confirmed.short_description = "Mark selected as Confirmed"
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
        self.message_user(request, f"{queryset.count()} booking(s) marked as Completed.")
    mark_as_completed.short_description = "Mark selected as Completed"
    
    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
        self.message_user(request, f"{queryset.count()} booking(s) marked as Cancelled.")
    mark_as_cancelled.short_description = "Mark selected as Cancelled"