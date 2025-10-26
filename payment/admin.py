from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'order_id',
        'get_booking_display',
        'get_user_display',
        'get_amount_display',
        'get_method_display',
        'status',
        'created_at',
        'paid_at',
    ]
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['order_id', 'transaction_id', 'user__username', 'booking__id']
    readonly_fields = [
        'order_id',
        'transaction_id',
        'transaction_ref',
        'created_at',
        'updated_at',
        'paid_at',
        'midtrans_response',
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('booking', 'user', 'amount', 'method')
        }),
        ('Transaction Details', {
            'fields': ('order_id', 'transaction_id', 'transaction_ref', 'status', 'payment_url')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at')
        }),
        ('Debug Information', {
            'fields': ('midtrans_response',),
            'classes': ('collapse',)
        }),
    )
    
    def get_booking_display(self, obj):
        """Display booking with fallback"""
        return obj.booking if obj.booking else '-'
    get_booking_display.short_description = 'Booking'
    
    def get_user_display(self, obj):
        """Display user with fallback"""
        return obj.user if obj.user else '-'
    get_user_display.short_description = 'User'
    
    def get_amount_display(self, obj):
        """Display amount formatted"""
        return f'Rp {obj.amount:,}' if obj.amount else '-'
    get_amount_display.short_description = 'Amount'
    
    def get_method_display(self, obj):
        """Display payment method with fallback"""
        if obj.method:
            return obj.get_method_display()
        return '-'
    get_method_display.short_description = 'Method'
    
    def has_add_permission(self, request):
        # Payments should only be created through the application flow
        return False
