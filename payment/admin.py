from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'order_id',
        'booking',
        'user',
        'amount',
        'method',
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
    
    def has_add_permission(self, request):
        # Payments should only be created through the application flow
        return False
