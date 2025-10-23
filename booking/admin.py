from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'coach', 'course', 'start_datetime', 'end_datetime', 'status', 'created_at']
    list_filter = ['status', 'start_datetime', 'created_at']
    search_fields = ['user__username', 'coach__user__username', 'course__title']
    date_hierarchy = 'start_datetime'
    ordering = ['-created_at']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Booking Information', {
            'fields': ('user', 'coach', 'course', 'status')
        }),
        ('Schedule', {
            'fields': ('start_datetime', 'end_datetime')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Actions untuk update status dari admin
    actions = ['mark_as_confirmed', 'mark_as_done', 'mark_as_canceled']
    
    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')
        self.message_user(request, f"{queryset.count()} booking(s) marked as Confirmed.")
    mark_as_confirmed.short_description = "Mark selected as Confirmed"
    
    def mark_as_done(self, request, queryset):
        queryset.update(status='done')
        self.message_user(request, f"{queryset.count()} booking(s) marked as Done.")
    mark_as_done.short_description = "Mark selected as Done"
    
    def mark_as_canceled(self, request, queryset):
        queryset.update(status='canceled')
        self.message_user(request, f"{queryset.count()} booking(s) marked as Canceled.")
    mark_as_canceled.short_description = "Mark selected as Canceled"