from django.contrib import admin
from .models import ScheduleSlot

@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ['id', 'coach', 'date', 'start_time', 'end_time', 'is_available', 'created_at']
    list_filter = ['is_available', 'date', 'coach']
    search_fields = ['coach__user__username', 'coach__user__first_name', 'coach__user__last_name']
    ordering = ['-date', 'start_time']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Coach', {
            'fields': ('coach',)
        }),
        ('Schedule', {
            'fields': ('date', 'start_time', 'end_time', 'is_available')
        }),
    )
    
    actions = ['mark_as_available', 'mark_as_unavailable', 'duplicate_to_next_week']
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} schedule(s) marked as available.')
    mark_as_available.short_description = "Mark selected as Available"
    
    def mark_as_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} schedule(s) marked as unavailable.')
    mark_as_unavailable.short_description = "Mark selected as Unavailable"
    
    def duplicate_to_next_week(self, request, queryset):
        """Duplicate selected schedules to next week"""
        from datetime import timedelta
        count = 0
        for slot in queryset:
            new_date = slot.date + timedelta(days=7)
            ScheduleSlot.objects.get_or_create(
                coach=slot.coach,
                date=new_date,
                start_time=slot.start_time,
                defaults={
                    'end_time': slot.end_time,
                    'is_available': slot.is_available
                }
            )
            count += 1
        self.message_user(request, f'{count} schedule(s) duplicated to next week.')
    duplicate_to_next_week.short_description = "Duplicate to next week"