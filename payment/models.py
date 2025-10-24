from django.db import models
from django.contrib.auth.models import User
from booking.models import Booking


class Payment(models.Model):
    """
    Payment model to track payment transactions via Midtrans
    """
    PAYMENT_METHOD_CHOICES = [
        ('credit_card', 'Credit Card'),
        ('bca_va', 'BCA Virtual Account'),
        ('mandiri_va', 'Mandiri Virtual Account'),
        ('bni_va', 'BNI Virtual Account'),
        ('bri_va', 'BRI Virtual Account'),
        ('permata_va', 'Permata Virtual Account'),
        ('cimb_va', 'CIMB Virtual Account'),
        ('other_va', 'Other Virtual Account'),
        ('indomaret', 'Indomaret'),
        ('alfamart', 'Alfamart'),
        ('gopay', 'GO-PAY'),
        ('akulaku', 'Akulaku'),
        ('shopeepay', 'ShopeePay'),
        ('kredivo', 'Kredivo'),
        ('qris', 'Other QRIS'),
        ('dana', 'Dana'),
        ('danamon_va', 'Danamon Virtual Account'),
        ('bsi_va', 'BSI Virtual Account'),
        ('seabank_va', 'SeaBank Virtual Account'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('settlement', 'Settlement'),
        ('capture', 'Capture'),
        ('deny', 'Deny'),
        ('cancel', 'Cancel'),
        ('expire', 'Expire'),
        ('failure', 'Failure'),
    ]
    
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='payments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    
    # Amount in Rupiah
    amount = models.IntegerField(help_text="Amount in IDR")
    
    # Payment method selected by user
    method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True)
    # Midtrans transaction details
    order_id = models.CharField(max_length=255, unique=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    transaction_ref = models.CharField(max_length=255, null=True, blank=True)
    
    # Payment status from Midtrans
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Payment URL from Midtrans (redirect or deeplink)
    payment_url = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    midtrans_response = models.JSONField(null=True, blank=True)
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['transaction_id']),
            models.Index(fields=['booking']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"Payment {self.order_id} - {self.status} - Rp {self.amount:,}"
    
    @property
    def is_successful(self):
        """Check if payment is successful"""
        return self.status in ['settlement', 'capture']
    
    @property
    def is_pending(self):
        """Check if payment is still pending"""
        return self.status == 'pending'
    
    @property
    def is_failed(self):
        """Check if payment failed"""
        return self.status in ['deny', 'cancel', 'expire', 'failure']
