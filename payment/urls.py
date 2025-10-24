from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    # Payment flow
    path('booking/<int:booking_id>/method/', views.payment_method_selection, name='method_selection'),
    path('booking/<int:booking_id>/process/', views.process_payment, name='process'),
    path('booking/<int:booking_id>/callback/', views.payment_callback, name='callback'),
    
    # Webhook from Midtrans
    path('webhook/midtrans/', views.midtrans_webhook, name='midtrans_webhook'),
    
    # Payment status check
    path('status/<int:payment_id>/', views.payment_status, name='status'),
]
