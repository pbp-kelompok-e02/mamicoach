from django.urls import path
from . import views

app_name = 'payment'

urlpatterns = [
    # Payment flow
    path('booking/<int:booking_id>/method/', views.payment_method_selection, name='method_selection'),
    path('booking/<int:booking_id>/process/', views.process_payment, name='process'),
    
    # Midtrans redirect URLs (query params: ?order_id=xxx&status_code=xxx&transaction_status=xxx)
    path('callback/', views.payment_callback, name='callback'),
    path('unfinish/', views.payment_unfinish, name='unfinish'),
    path('error/', views.payment_error, name='error'),
    
    # Webhook from Midtrans (notification endpoint)
    path('webhook/midtrans', views.midtrans_webhook, name='midtrans_webhook'),
    
    # Payment status check
    path('status/<int:payment_id>/', views.payment_status, name='status'),
]
