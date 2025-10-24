import json
import uuid
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST
from django.contrib import messages
from django.urls import reverse
import requests

from booking.models import Booking
from .models import Payment
from .midtrans_service import MidtransService


@login_required
@require_http_methods(["GET"])
def payment_method_selection(request, booking_id):
    """
    Show payment method selection page
    User is redirected here from booking flow
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Check if booking is in pending status
    if booking.status != 'pending':
        messages.error(request, f'This booking is already {booking.status}. Payment is only available for pending bookings.')
        return redirect('booking:history')  # Adjust redirect as needed
    
    # Get course details
    course = booking.course
    coach = booking.coach
    
    # Calculate amount (assuming course has a price field)
    amount = getattr(course, 'price', 0)  # Adjust based on your Course model
    
    context = {
        'booking': booking,
        'course': course,
        'coach': coach,
        'amount': amount,
        'payment_methods': Payment.PAYMENT_METHOD_CHOICES,
    }
    
    return render(request, 'payment/method_selection.html', context)


@login_required
@require_POST
def process_payment(request, booking_id):
    """
    Process payment: create Midtrans transaction and redirect to payment URL
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Validate booking status
    if booking.status != 'pending':
        return JsonResponse({
            'success': False,
            'error': f'Booking is already {booking.status}. Cannot process payment.'
        }, status=400)
    
    # Get payment method from request
    payment_method = request.POST.get('payment_method')
    
    if not payment_method:
        return JsonResponse({
            'success': False,
            'error': 'Payment method is required'
        }, status=400)
    
    # Validate payment method
    valid_methods = [choice[0] for choice in Payment.PAYMENT_METHOD_CHOICES]
    if payment_method not in valid_methods:
        return JsonResponse({
            'success': False,
            'error': 'Invalid payment method'
        }, status=400)
    
    # Get course and amount
    course = booking.course
    amount = getattr(course, 'price', 0)
    
    if amount <= 0:
        return JsonResponse({
            'success': False,
            'error': 'Invalid course price'
        }, status=400)
    
    # Generate unique order ID
    order_id = f"MAMI-{booking.id}-{uuid.uuid4().hex[:8].upper()}"
    
    # Create Payment record
    payment = Payment.objects.create(
        booking=booking,
        user=request.user,
        amount=amount,
        method=payment_method,
        order_id=order_id,
        status='pending'
    )
    
    # Prepare Midtrans request
    midtrans = MidtransService()
    
    customer_details = {
        'first_name': request.user.first_name or request.user.username,
        'last_name': request.user.last_name or '',
        'email': request.user.email or f'{request.user.username}@example.com',
        'phone': getattr(request.user, 'phone', '081234567890'),  # Adjust based on your User model
    }
    
    item_details = [
        {
            'id': course.id,
            'price': amount,
            'quantity': 1,
            'name': course.title[:50],  # Limit to 50 chars for Midtrans
        }
    ]
    
    # Create Midtrans transaction
    result = midtrans.create_transaction(
        order_id=order_id,
        amount=amount,
        customer_details=customer_details,
        item_details=item_details,
        payment_method=payment_method
    )
    
    if not result.get('success'):
        payment.status = 'failure'
        payment.midtrans_response = result
        payment.save()
        
        return JsonResponse({
            'success': False,
            'error': 'Failed to create payment transaction',
            'details': result.get('error')
        }, status=500)
    
    # Update payment with Midtrans response
    payment.payment_url = result.get('redirect_url')
    payment.midtrans_response = result.get('response')
    payment.save()
    
    # Return redirect URL for frontend
    return JsonResponse({
        'success': True,
        'payment_id': payment.id,
        'redirect_url': result.get('redirect_url'),
        'token': result.get('token'),
    })


@csrf_exempt
@require_POST
def midtrans_webhook(request):
    """
    Webhook endpoint for Midtrans payment notifications
    This endpoint receives POST requests from Midtrans when payment status changes
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
        
        order_id = data.get('order_id')
        transaction_status = data.get('transaction_status')
        fraud_status = data.get('fraud_status')
        status_code = data.get('status_code')
        gross_amount = data.get('gross_amount')
        signature_key = data.get('signature_key')
        transaction_id = data.get('transaction_id')
        
        # Verify signature
        midtrans = MidtransService()
        is_valid = midtrans.verify_signature(
            order_id, status_code, gross_amount, signature_key
        )
        
        if not is_valid:
            return JsonResponse({
                'success': False,
                'error': 'Invalid signature'
            }, status=403)
        
        # Get payment record
        try:
            payment = Payment.objects.get(order_id=order_id)
        except Payment.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Payment not found'
            }, status=404)
        
        # Update payment status based on Midtrans status
        payment.transaction_id = transaction_id
        payment.midtrans_response = data
        
        # Map Midtrans status to our status
        if transaction_status == 'capture':
            if fraud_status == 'accept':
                payment.status = 'capture'
                payment.paid_at = datetime.now()
            else:
                payment.status = 'pending'
        elif transaction_status == 'settlement':
            payment.status = 'settlement'
            payment.paid_at = datetime.now()
        elif transaction_status == 'pending':
            payment.status = 'pending'
        elif transaction_status in ['deny', 'cancel', 'expire']:
            payment.status = transaction_status
        elif transaction_status == 'failure':
            payment.status = 'failure'
        
        payment.save()
        
        # If payment is successful, mark booking as paid
        if payment.is_successful:
            booking = payment.booking
            if booking.status == 'pending':
                # Call the booking API to mark as paid
                mark_booking_as_paid(booking.id, payment.id, payment.method)
        
        return JsonResponse({
            'success': True,
            'message': 'Notification processed'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def mark_booking_as_paid(booking_id: int, payment_id: int, payment_method: str):
    """
    Internal function to call booking API and mark booking as paid
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        if booking.status == 'pending':
            booking.status = 'paid'
            booking.save()
            return True
    except Booking.DoesNotExist:
        pass
    return False


@login_required
def payment_callback(request, booking_id):
    """
    Callback page after user completes/cancels payment on Midtrans page
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    # Get latest payment for this booking
    payment = Payment.objects.filter(booking=booking).order_by('-created_at').first()
    
    if not payment:
        messages.error(request, 'Payment record not found')
        return redirect('booking:history')
    
    # Check payment status from Midtrans
    midtrans = MidtransService()
    status_result = midtrans.get_transaction_status(payment.order_id)
    
    if status_result.get('success'):
        status_data = status_result.get('data', {})
        transaction_status = status_data.get('transaction_status')
        
        # Update local payment status
        if transaction_status == 'settlement' or transaction_status == 'capture':
            payment.status = transaction_status
            payment.paid_at = datetime.now()
            payment.save()
            
            # Mark booking as paid
            if booking.status == 'pending':
                booking.status = 'paid'
                booking.save()
    
    context = {
        'booking': booking,
        'payment': payment,
        'is_success': payment.is_successful,
        'is_pending': payment.is_pending,
        'is_failed': payment.is_failed,
    }
    
    return render(request, 'payment/callback.html', context)


@login_required
def payment_status(request, payment_id):
    """
    API endpoint to check payment status
    """
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)
    
    # Optionally refresh status from Midtrans
    if request.GET.get('refresh') == 'true':
        midtrans = MidtransService()
        result = midtrans.get_transaction_status(payment.order_id)
        
        if result.get('success'):
            status_data = result.get('data', {})
            transaction_status = status_data.get('transaction_status')
            
            if transaction_status in ['settlement', 'capture']:
                payment.status = transaction_status
                payment.paid_at = datetime.now()
                payment.save()
                
                # Update booking
                if payment.booking.status == 'pending':
                    payment.booking.status = 'paid'
                    payment.booking.save()
    
    return JsonResponse({
        'success': True,
        'payment_id': payment.id,
        'order_id': payment.order_id,
        'status': payment.status,
        'is_successful': payment.is_successful,
        'is_pending': payment.is_pending,
        'is_failed': payment.is_failed,
        'amount': payment.amount,
        'method': payment.method,
        'booking_id': payment.booking.id,
        'booking_status': payment.booking.status,
    })
