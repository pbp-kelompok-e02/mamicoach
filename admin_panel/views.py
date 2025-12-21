"""
Admin panel views for managing the MamiCoach platform
"""
import json
import jwt
from datetime import datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum, Q
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.conf import settings
from functools import wraps

from booking.models import Booking
from payment.models import Payment
from courses_and_coach.models import Course
from user_profile.models import CoachProfile, UserProfile, AdminVerification
from .models import AdminSettings, AdminActivityLog, AdminUser


# ==================== JWT Configuration ====================

# JWT settings - uses Django's SECRET_KEY for signing
JWT_SECRET = settings.SECRET_KEY
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRE_HOURS = 24  # Access token expires in 24 hours
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7   # Refresh token expires in 7 days


def generate_jwt_tokens(admin_user):
    """Generate access and refresh JWT tokens for an admin user"""
    now = datetime.utcnow()
    
    # Access token payload
    access_payload = {
        'user_id': admin_user.id,
        'username': admin_user.username,
        'email': admin_user.email,
        'type': 'access',
        'iat': now,
        'exp': now + timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS),
    }
    
    # Refresh token payload
    refresh_payload = {
        'user_id': admin_user.id,
        'type': 'refresh',
        'iat': now,
        'exp': now + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    
    access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600,  # in seconds
        'token_type': 'Bearer'
    }


def decode_jwt_token(token):
    """Decode and validate a JWT token. Returns payload or None if invalid."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # Token has expired
    except jwt.InvalidTokenError:
        return None  # Invalid token


# ==================== JSON API Authentication ====================

def api_admin_login_required(view_func):
    """Decorator for JSON API endpoints - checks admin session or JWT token"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check session-based auth first (for web admin panel)
        if 'admin_user_id' in request.session:
            try:
                admin_user = AdminUser.objects.get(id=request.session['admin_user_id'], is_active=True)
                request.admin_user = admin_user
                return view_func(request, *args, **kwargs)
            except AdminUser.DoesNotExist:
                pass
        
        # Check Authorization header for JWT token (for Flutter)
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Remove 'Bearer ' prefix
            payload = decode_jwt_token(token)
            
            if payload and payload.get('type') == 'access':
                try:
                    admin_user = AdminUser.objects.get(id=payload['user_id'], is_active=True)
                    request.admin_user = admin_user
                    return view_func(request, *args, **kwargs)
                except AdminUser.DoesNotExist:
                    return JsonResponse({
                        'status': False,
                        'message': 'User not found or inactive'
                    }, status=401)
            else:
                return JsonResponse({
                    'status': False,
                    'message': 'Invalid or expired token'
                }, status=401)
        
        return JsonResponse({
            'status': False,
            'message': 'Authentication required. Provide Bearer token in Authorization header.'
        }, status=401)
    return wrapper


# ==================== JSON API Endpoints ====================

@csrf_exempt
@require_http_methods(["POST"])
def api_admin_login(request):
    """
    Admin login API endpoint for Flutter
    POST /admin/api/login/
    Request: { "username": "...", "password": "..." }
    Response: { "status": true, "message": "...", "data": { "access_token": "...", "refresh_token": "...", "user": {...} } }
    """
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return JsonResponse({
                'status': False,
                'message': 'Username and password are required'
            }, status=400)
        
        try:
            admin_user = AdminUser.objects.get(username=username, is_active=True)
            if admin_user.check_password(password):
                admin_user.last_login = timezone.now()
                admin_user.save()
                
                # Generate JWT tokens
                tokens = generate_jwt_tokens(admin_user)
                
                log_admin_activity(admin_user, 'login', 'auth', 'Admin logged in via API', request)
                
                return JsonResponse({
                    'status': True,
                    'message': 'Login successful',
                    'data': {
                        'access_token': tokens['access_token'],
                        'refresh_token': tokens['refresh_token'],
                        'expires_in': tokens['expires_in'],
                        'token_type': tokens['token_type'],
                        'user': {
                            'id': admin_user.id,
                            'username': admin_user.username,
                            'email': admin_user.email,
                            'is_superuser': True,
                        }
                    }
                })
            else:
                return JsonResponse({
                    'status': False,
                    'message': 'Invalid credentials'
                }, status=401)
        except AdminUser.DoesNotExist:
            return JsonResponse({
                'status': False,
                'message': 'Invalid credentials'
            }, status=401)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'message': 'Invalid JSON data'
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_admin_refresh_token(request):
    """
    Refresh access token using refresh token
    POST /admin/api/refresh/
    Request: { "refresh_token": "..." }
    Response: { "status": true, "data": { "access_token": "...", "expires_in": ... } }
    """
    try:
        data = json.loads(request.body)
        refresh_token = data.get('refresh_token', '')
        
        if not refresh_token:
            return JsonResponse({
                'status': False,
                'message': 'Refresh token is required'
            }, status=400)
        
        payload = decode_jwt_token(refresh_token)
        
        if not payload or payload.get('type') != 'refresh':
            return JsonResponse({
                'status': False,
                'message': 'Invalid or expired refresh token'
            }, status=401)
        
        try:
            admin_user = AdminUser.objects.get(id=payload['user_id'], is_active=True)
            
            # Generate new access token only
            now = datetime.utcnow()
            access_payload = {
                'user_id': admin_user.id,
                'username': admin_user.username,
                'email': admin_user.email,
                'type': 'access',
                'iat': now,
                'exp': now + timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS),
            }
            new_access_token = jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
            
            return JsonResponse({
                'status': True,
                'message': 'Token refreshed successfully',
                'data': {
                    'access_token': new_access_token,
                    'expires_in': JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600,
                    'token_type': 'Bearer'
                }
            })
        except AdminUser.DoesNotExist:
            return JsonResponse({
                'status': False,
                'message': 'User not found or inactive'
            }, status=401)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'message': 'Invalid JSON data'
        }, status=400)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["POST"])
def api_admin_logout(request):
    """
    Admin logout API endpoint
    POST /api/admin/logout/
    """
    log_admin_activity(request.admin_user, 'logout', 'auth', 'Admin logged out via API', request)
    request.session.flush()
    return JsonResponse({
        'status': True,
        'message': 'Logout successful'
    })


@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_bookings_list(request):
    """
    List all bookings with filtering and pagination (JSON API)
    GET /api/admin/bookings/
    Query params: status, search, page, per_page
    """
    bookings = Booking.objects.select_related('user', 'course', 'coach').order_by('-created_at')
    
    # Status filter
    status = request.GET.get('status', 'all')
    if status and status != 'all':
        bookings = bookings.filter(status=status)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        bookings = bookings.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(course__title__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10
    
    paginator = Paginator(bookings, per_page)
    try:
        paginated_bookings = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        paginated_bookings = paginator.page(1)
    
    # Serialize bookings
    bookings_data = []
    for booking in paginated_bookings:
        bookings_data.append({
            'id': booking.id,
            'user': {
                'id': booking.user.id,
                'username': booking.user.username,
                'email': booking.user.email,
            },
            'coach': {
                'id': booking.coach.id,
                'name': booking.coach.user.get_full_name() or booking.coach.user.username,
            } if booking.coach else None,
            'course': {
                'id': booking.course.id,
                'title': booking.course.title,
                'price': float(booking.course.price) if booking.course.price else 0,
            },
            'start_datetime': booking.start_datetime.isoformat() if booking.start_datetime else None,
            'end_datetime': booking.end_datetime.isoformat() if booking.end_datetime else None,
            'status': booking.status,
            'created_at': booking.created_at.isoformat(),
            'updated_at': booking.updated_at.isoformat(),
        })
    
    log_admin_activity(request.admin_user, 'view', 'bookings', 'Viewed bookings via API', request)
    
    return JsonResponse({
        'status': True,
        'message': 'Bookings retrieved successfully',
        'data': {
            'bookings': bookings_data,
            'pagination': {
                'current_page': paginated_bookings.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'per_page': per_page,
                'has_next': paginated_bookings.has_next(),
                'has_previous': paginated_bookings.has_previous(),
            }
        }
    })


@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_booking_detail(request, booking_id):
    """
    Get single booking details (JSON API)
    GET /api/admin/bookings/<booking_id>/
    """
    try:
        booking = Booking.objects.select_related('user', 'course', 'coach').get(id=booking_id)
        
        booking_data = {
            'id': booking.id,
            'user': {
                'id': booking.user.id,
                'username': booking.user.username,
                'email': booking.user.email,
                'first_name': booking.user.first_name,
                'last_name': booking.user.last_name,
            },
            'coach': {
                'id': booking.coach.id,
                'name': booking.coach.user.get_full_name() or booking.coach.user.username,
                'email': booking.coach.user.email,
            } if booking.coach else None,
            'course': {
                'id': booking.course.id,
                'title': booking.course.title,
                'description': booking.course.description,
                'price': float(booking.course.price) if booking.course.price else 0,
            },
            'start_datetime': booking.start_datetime.isoformat() if booking.start_datetime else None,
            'end_datetime': booking.end_datetime.isoformat() if booking.end_datetime else None,
            'status': booking.status,
            'created_at': booking.created_at.isoformat(),
            'updated_at': booking.updated_at.isoformat(),
        }
        
        return JsonResponse({
            'status': True,
            'message': 'Booking retrieved successfully',
            'data': booking_data
        })
    except Booking.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Booking not found'
        }, status=404)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["POST", "PUT", "PATCH"])
def api_booking_update_status(request, booking_id):
    """
    Update booking status (JSON API)
    POST/PUT/PATCH /api/admin/bookings/<booking_id>/update-status/
    Request: { "status": "pending|paid|confirmed|done|canceled" }
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        data = json.loads(request.body)
        new_status = data.get('status', '').strip()
        
        valid_statuses = dict(Booking.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return JsonResponse({
                'status': False,
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=400)
        
        old_status = booking.status
        booking.status = new_status
        booking.save()
        
        log_admin_activity(
            request.admin_user, 'update', 'bookings',
            f'Updated booking #{booking.id} status from {old_status} to {new_status} via API',
            request
        )
        
        return JsonResponse({
            'status': True,
            'message': f'Booking status updated to {new_status}',
            'data': {
                'id': booking.id,
                'old_status': old_status,
                'new_status': new_status,
            }
        })
    except Booking.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Booking not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'message': 'Invalid JSON data'
        }, status=400)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["DELETE", "POST"])
def api_booking_delete(request, booking_id):
    """
    Delete a booking (JSON API)
    DELETE /api/admin/bookings/<booking_id>/delete/
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        booking_info = f"#{booking.id} - {booking.user.username} - {booking.course.title}"
        booking.delete()
        
        log_admin_activity(
            request.admin_user, 'delete', 'bookings',
            f'Deleted booking {booking_info} via API',
            request
        )
        
        return JsonResponse({
            'status': True,
            'message': 'Booking deleted successfully'
        })
    except Booking.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Booking not found'
        }, status=404)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_payments_list(request):
    """
    List all payments with filtering and pagination (JSON API)
    GET /api/admin/payments/
    Query params: status, search, page, per_page
    """
    payments = Payment.objects.select_related('booking__user', 'booking__course', 'user').order_by('-created_at')
    
    # Status filter
    status = request.GET.get('status', 'all')
    if status and status != 'all':
        payments = payments.filter(status=status)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        payments = payments.filter(
            Q(order_id__icontains=search_query) |
            Q(booking__user__username__icontains=search_query) |
            Q(booking__user__email__icontains=search_query) |
            Q(booking__id__icontains=search_query)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10
    
    paginator = Paginator(payments, per_page)
    try:
        paginated_payments = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        paginated_payments = paginator.page(1)
    
    # Serialize payments
    payments_data = []
    for payment in paginated_payments:
        payments_data.append({
            'id': payment.id,
            'order_id': payment.order_id,
            'transaction_id': payment.transaction_id,
            'booking': {
                'id': payment.booking.id,
                'user': {
                    'id': payment.booking.user.id,
                    'username': payment.booking.user.username,
                },
                'course': {
                    'id': payment.booking.course.id,
                    'title': payment.booking.course.title,
                } if payment.booking.course else None,
            },
            'amount': payment.amount,
            'method': payment.method,
            'method_display': payment.get_method_display() if payment.method else None,
            'status': payment.status,
            'is_successful': payment.is_successful,
            'is_pending': payment.is_pending,
            'is_failed': payment.is_failed,
            'payment_url': payment.payment_url,
            'created_at': payment.created_at.isoformat(),
            'updated_at': payment.updated_at.isoformat(),
            'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
        })
    
    log_admin_activity(request.admin_user, 'view', 'payments', 'Viewed payments via API', request)
    
    return JsonResponse({
        'status': True,
        'message': 'Payments retrieved successfully',
        'data': {
            'payments': payments_data,
            'pagination': {
                'current_page': paginated_payments.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'per_page': per_page,
                'has_next': paginated_payments.has_next(),
                'has_previous': paginated_payments.has_previous(),
            }
        }
    })


@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_payment_detail(request, payment_id):
    """
    Get single payment details (JSON API)
    GET /api/admin/payments/<payment_id>/
    """
    try:
        payment = Payment.objects.select_related('booking__user', 'booking__course', 'user').get(id=payment_id)
        
        payment_data = {
            'id': payment.id,
            'order_id': payment.order_id,
            'transaction_id': payment.transaction_id,
            'transaction_ref': payment.transaction_ref,
            'booking': {
                'id': payment.booking.id,
                'user': {
                    'id': payment.booking.user.id,
                    'username': payment.booking.user.username,
                    'email': payment.booking.user.email,
                },
                'course': {
                    'id': payment.booking.course.id,
                    'title': payment.booking.course.title,
                    'price': float(payment.booking.course.price) if payment.booking.course.price else 0,
                } if payment.booking.course else None,
                'status': payment.booking.status,
            },
            'user': {
                'id': payment.user.id,
                'username': payment.user.username,
                'email': payment.user.email,
            },
            'amount': payment.amount,
            'method': payment.method,
            'method_display': payment.get_method_display() if payment.method else None,
            'status': payment.status,
            'is_successful': payment.is_successful,
            'is_pending': payment.is_pending,
            'is_failed': payment.is_failed,
            'payment_url': payment.payment_url,
            'midtrans_response': payment.midtrans_response,
            'created_at': payment.created_at.isoformat(),
            'updated_at': payment.updated_at.isoformat(),
            'paid_at': payment.paid_at.isoformat() if payment.paid_at else None,
        }
        
        return JsonResponse({
            'status': True,
            'message': 'Payment retrieved successfully',
            'data': payment_data
        })
    except Payment.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Payment not found'
        }, status=404)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["POST", "PUT", "PATCH"])
def api_payment_update_status(request, payment_id):
    """
    Update payment status (JSON API)
    POST/PUT/PATCH /api/admin/payments/<payment_id>/update-status/
    Request: { "status": "pending|settlement|capture|deny|cancel|expire|failure" }
    """
    try:
        payment = Payment.objects.get(id=payment_id)
        data = json.loads(request.body)
        new_status = data.get('status', '').strip()
        
        valid_statuses = dict(Payment.STATUS_CHOICES).keys()
        if new_status not in valid_statuses:
            return JsonResponse({
                'status': False,
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }, status=400)
        
        old_status = payment.status
        payment.status = new_status
        
        # If payment is successful, update paid_at
        if new_status in ['settlement', 'capture'] and not payment.paid_at:
            payment.paid_at = timezone.now()
        
        payment.save()
        
        # Update booking status if payment is successful
        if new_status in ['settlement', 'capture'] and payment.booking.status == 'pending':
            payment.booking.status = 'paid'
            payment.booking.save()
        
        log_admin_activity(
            request.admin_user, 'update', 'payments',
            f'Updated payment {payment.order_id} status from {old_status} to {new_status} via API',
            request
        )
        
        return JsonResponse({
            'status': True,
            'message': f'Payment status updated to {new_status}',
            'data': {
                'id': payment.id,
                'order_id': payment.order_id,
                'old_status': old_status,
                'new_status': new_status,
            }
        })
    except Payment.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Payment not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'message': 'Invalid JSON data'
        }, status=400)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_dashboard_stats(request):
    """
    Get dashboard statistics (JSON API)
    GET /api/admin/dashboard/
    """
    # Get statistics
    total_users = UserProfile.objects.count()
    total_coaches = CoachProfile.objects.count()
    total_courses = Course.objects.count()
    total_bookings = Booking.objects.count()
    
    # Bookings by status
    pending_bookings = Booking.objects.filter(status='pending').count()
    paid_bookings = Booking.objects.filter(status='paid').count()
    confirmed_bookings = Booking.objects.filter(status='confirmed').count()
    done_bookings = Booking.objects.filter(status='done').count()
    canceled_bookings = Booking.objects.filter(status='canceled').count()
    
    # Payment statistics
    total_revenue = Payment.objects.filter(status__in=['settlement', 'capture']).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    pending_payments = Payment.objects.filter(status='pending').count()
    successful_payments = Payment.objects.filter(status__in=['settlement', 'capture']).count()
    failed_payments = Payment.objects.filter(status__in=['deny', 'cancel', 'expire', 'failure']).count()
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related('user', 'course').order_by('-created_at')[:5]
    recent_bookings_data = [{
        'id': b.id,
        'user': b.user.username,
        'course': b.course.title,
        'status': b.status,
        'created_at': b.created_at.isoformat(),
    } for b in recent_bookings]
    
    # Recent payments
    recent_payments = Payment.objects.select_related('booking__user').order_by('-created_at')[:5]
    recent_payments_data = [{
        'id': p.id,
        'order_id': p.order_id,
        'user': p.booking.user.username,
        'amount': p.amount,
        'status': p.status,
        'created_at': p.created_at.isoformat(),
    } for p in recent_payments]
    
    # New users this month
    from django.contrib.auth.models import User
    now = timezone.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = User.objects.filter(date_joined__gte=start_of_month).count()
    
    # Bookings trend - last 7 days
    from datetime import timedelta
    bookings_trend = []
    day_labels = ['Sen', 'Sel', 'Rab', 'Kam', 'Jum', 'Sab', 'Min']
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        count = Booking.objects.filter(created_at__gte=day_start, created_at__lt=day_end).count()
        day_index = (day.weekday() + 1) % 7  # Convert Monday=0 to Sunday=0
        bookings_trend.append({
            'label': day_labels[day_index],
            'value': count
        })
    
    # Revenue trend - last 6 months
    from dateutil.relativedelta import relativedelta
    revenue_trend = []
    month_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des']
    for i in range(5, -1, -1):
        month_date = now - relativedelta(months=i)
        month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i == 0:
            month_end = now
        else:
            next_month = month_start + relativedelta(months=1)
            month_end = next_month
        
        revenue = Payment.objects.filter(
            status__in=['settlement', 'capture'],
            paid_at__gte=month_start,
            paid_at__lt=month_end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        revenue_trend.append({
            'label': month_labels[month_date.month - 1],
            'value': revenue
        })
    
    # Top categories - top 5 course categories by booking count
    from django.db.models import Count
    category_bookings = Booking.objects.values('course__category__name').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    total_categorized_bookings = sum(item['count'] for item in category_bookings)
    top_categories = []
    for item in category_bookings:
        category_name = item['course__category__name'] or 'Uncategorized'
        count = item['count']
        percentage = (count / total_categorized_bookings * 100) if total_categorized_bookings > 0 else 0
        top_categories.append({
            'name': category_name,
            'count': count,
            'percentage': round(percentage, 1)
        })
    
    log_admin_activity(request.admin_user, 'view', 'dashboard', 'Viewed dashboard via API', request)
    
    return JsonResponse({
        'status': True,
        'message': 'Dashboard stats retrieved successfully',
        'data': {
            'overview': {
                'total_users': total_users,
                'total_coaches': total_coaches,
                'total_courses': total_courses,
                'total_bookings': total_bookings,
                'pending_bookings': pending_bookings,
                'completed_bookings': done_bookings,
                'total_revenue': total_revenue,
                'new_users_this_month': new_users_this_month,
            },
            'bookings': {
                'total': total_bookings,
                'pending': pending_bookings,
                'paid': paid_bookings,
                'confirmed': confirmed_bookings,
                'done': done_bookings,
                'canceled': canceled_bookings,
            },
            'payments': {
                'total_revenue': total_revenue,
                'pending_amount': Payment.objects.filter(status='pending').aggregate(total=Sum('amount'))['total'] or 0,
                'successful_amount': total_revenue,
            },
            'bookings_trend': bookings_trend,
            'revenue_trend': revenue_trend,
            'top_categories': top_categories,
            'recent_bookings': recent_bookings_data,
            'recent_payments': recent_payments_data,
        }
    })


# ==================== Users API Endpoints ====================

@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_users_list(request):
    """
    List all users with filtering and pagination (JSON API)
    GET /admin/api/users/
    Query params: search, page, per_page
    """
    from django.contrib.auth.models import User
    
    users = User.objects.select_related('userprofile').order_by('-date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10
    
    paginator = Paginator(users, per_page)
    try:
        paginated_users = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        paginated_users = paginator.page(1)
    
    # Serialize users
    users_data = []
    for user in paginated_users:
        profile = getattr(user, 'userprofile', None)
        users_data.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'profile': {
                'id': profile.id if profile else None,
                'phone': profile.phone if profile else None,
                'profile_picture': profile.profile_picture.url if profile and profile.profile_picture else None,
            } if profile else None,
        })
    
    log_admin_activity(request.admin_user, 'view', 'users', 'Viewed users via API', request)
    
    return JsonResponse({
        'status': True,
        'message': 'Users retrieved successfully',
        'data': {
            'users': users_data,
            'pagination': {
                'current_page': paginated_users.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'per_page': per_page,
                'has_next': paginated_users.has_next(),
                'has_previous': paginated_users.has_previous(),
            }
        }
    })


@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_user_detail(request, user_id):
    """
    Get single user details (JSON API)
    GET /admin/api/users/<user_id>/
    """
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.select_related('userprofile').get(id=user_id)
        profile = getattr(user, 'userprofile', None)
        
        # Get user's bookings count
        bookings_count = Booking.objects.filter(user=user).count()
        payments_count = Payment.objects.filter(user=user).count()
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'date_joined': user.date_joined.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None,
            'profile': {
                'id': profile.id if profile else None,
                'phone': profile.phone if profile else None,
                'bio': profile.bio if profile else None,
                'profile_picture': profile.profile_picture.url if profile and profile.profile_picture else None,
            } if profile else None,
            'stats': {
                'bookings_count': bookings_count,
                'payments_count': payments_count,
            }
        }
        
        return JsonResponse({
            'status': True,
            'message': 'User retrieved successfully',
            'data': user_data
        })
    except User.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'User not found'
        }, status=404)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["POST", "PUT", "PATCH"])
def api_user_update_status(request, user_id):
    """
    Update user status (JSON API)
    POST/PUT/PATCH /admin/api/users/<user_id>/update-status/
    Request: { "is_active": true/false }
    """
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.get(id=user_id)
        data = json.loads(request.body)
        
        if 'is_active' not in data:
            return JsonResponse({
                'status': False,
                'message': 'is_active field is required'
            }, status=400)
        
        new_status = data.get('is_active')
        if not isinstance(new_status, bool):
            return JsonResponse({
                'status': False,
                'message': 'is_active must be a boolean value'
            }, status=400)
        
        old_status = user.is_active
        user.is_active = new_status
        user.save()
        
        log_admin_activity(
            request.admin_user, 'update', 'users',
            f'Updated user {user.username} active status from {old_status} to {new_status} via API',
            request
        )
        
        return JsonResponse({
            'status': True,
            'message': 'User status updated successfully',
            'data': {
                'id': user.id,
                'is_active': new_status,
                'updated_at': timezone.now().isoformat(),
            }
        })
    except User.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'User not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'message': 'Invalid JSON data'
        }, status=400)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["DELETE", "POST"])
def api_user_delete(request, user_id):
    """
    Delete a user (JSON API)
    DELETE /admin/api/users/<user_id>/delete/
    """
    from django.contrib.auth.models import User
    
    try:
        user = User.objects.get(id=user_id)
        username = user.username
        user.delete()
        
        log_admin_activity(
            request.admin_user, 'delete', 'users',
            f'Deleted user {username} via API',
            request
        )
        
        return JsonResponse({
            'status': True,
            'message': f'User {username} deleted successfully'
        })
    except User.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'User not found'
        }, status=404)


# ==================== Coaches API Endpoints ====================

@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_coaches_list(request):
    """
    List all coaches with filtering and pagination (JSON API)
    GET /admin/api/coaches/
    Query params: search, verified, page, per_page
    """
    coaches = CoachProfile.objects.select_related('user').prefetch_related('adminverification').order_by('-id')
    
    # Filter by verified status
    verified = request.GET.get('verified', '').strip().lower()
    if verified == 'true':
        coaches = coaches.filter(verified=True)
    elif verified == 'false':
        coaches = coaches.filter(verified=False)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        coaches = coaches.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10
    
    paginator = Paginator(coaches, per_page)
    try:
        paginated_coaches = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        paginated_coaches = paginator.page(1)
    
    # Serialize coaches
    coaches_data = []
    for coach in paginated_coaches:
        verification = coach.adminverification.first() if hasattr(coach, 'adminverification') else None
        coaches_data.append({
            'id': coach.id,
            'user': {
                'id': coach.user.id,
                'username': coach.user.username,
                'email': coach.user.email,
                'first_name': coach.user.first_name,
                'last_name': coach.user.last_name,
            },
            'verified': coach.verified,
            'bio': coach.bio,
            'expertise': coach.expertise,
            'rating': coach.rating,
            'rating_count': coach.rating_count,
            'total_minutes_coached': coach.total_minutes_coached,
            'balance': coach.balance,
            'profile_picture': coach.profile_picture.url if coach.profile_picture else None,
            'verification_status': verification.status if verification else 'pending',
            'created_at': coach.user.date_joined.isoformat(),
        })
    
    log_admin_activity(request.admin_user, 'view', 'coaches', 'Viewed coaches via API', request)
    
    return JsonResponse({
        'status': True,
        'message': 'Coaches retrieved successfully',
        'data': {
            'coaches': coaches_data,
            'pagination': {
                'current_page': paginated_coaches.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'per_page': per_page,
                'has_next': paginated_coaches.has_next(),
                'has_previous': paginated_coaches.has_previous(),
            }
        }
    })


@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_coach_detail(request, coach_id):
    """
    Get single coach details (JSON API)
    GET /admin/api/coaches/<coach_id>/
    """
    try:
        coach = CoachProfile.objects.select_related('user').prefetch_related('adminverification').get(id=coach_id)
        verification = coach.adminverification.first() if hasattr(coach, 'adminverification') else None
        
        # Get coach's courses and bookings count
        courses_count = Course.objects.filter(coach=coach).count()
        bookings_count = Booking.objects.filter(coach=coach).count()
        
        coach_data = {
            'id': coach.id,
            'user': {
                'id': coach.user.id,
                'username': coach.user.username,
                'email': coach.user.email,
                'first_name': coach.user.first_name,
                'last_name': coach.user.last_name,
                'is_active': coach.user.is_active,
                'date_joined': coach.user.date_joined.isoformat(),
            },
            'verified': coach.verified,
            'bio': coach.bio,
            'expertise': coach.expertise,
            'rating': coach.rating,
            'rating_count': coach.rating_count,
            'total_minutes_coached': coach.total_minutes_coached,
            'balance': coach.balance,
            'profile_picture': coach.profile_picture.url if coach.profile_picture else None,
            'verification': {
                'status': verification.status if verification else 'pending',
                'certificate_url': verification.certificate_url if verification else None,
                'notes': verification.notes if verification else None,
            } if verification else None,
            'stats': {
                'courses_count': courses_count,
                'bookings_count': bookings_count,
            }
        }
        
        return JsonResponse({
            'status': True,
            'message': 'Coach retrieved successfully',
            'data': coach_data
        })
    except CoachProfile.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Coach not found'
        }, status=404)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["POST", "PUT", "PATCH"])
def api_coach_verify(request, coach_id):
    """
    Update coach verification status (JSON API)
    POST /admin/api/coaches/<coach_id>/verify/
    Request: { "action": "verify|unverify|approve|reject", "notes": "optional notes" }
    """
    try:
        coach = CoachProfile.objects.get(id=coach_id)
        data = json.loads(request.body)
        action = data.get('action', '').strip().lower()
        notes = data.get('notes', '')
        
        valid_actions = ['verify', 'unverify', 'approve', 'reject']
        if action not in valid_actions:
            return JsonResponse({
                'status': False,
                'message': f'Invalid action. Must be one of: {", ".join(valid_actions)}'
            }, status=400)
        
        # Get or create admin verification record
        admin_verification, created = AdminVerification.objects.get_or_create(
            coach=coach,
            defaults={'certificate_url': '', 'status': 'pending'}
        )
        
        if action == 'verify':
            coach.verified = True
            coach.save()
            message = f'Coach {coach.user.username} verified badge added'
            
        elif action == 'unverify':
            coach.verified = False
            coach.save()
            message = f'Coach {coach.user.username} verified badge removed'
            
        elif action == 'approve':
            admin_verification.status = 'approved'
            admin_verification.notes = notes or f'Approved by {request.admin_user.username}'
            admin_verification.save()
            coach.verified = True
            coach.save()
            message = f'Coach {coach.user.username} approved and verified'
            
        elif action == 'reject':
            admin_verification.status = 'rejected'
            admin_verification.notes = notes or f'Rejected by {request.admin_user.username}'
            admin_verification.save()
            coach.verified = False
            coach.save()
            message = f'Coach {coach.user.username} rejected'
        
        log_admin_activity(
            request.admin_user, 'update', 'coaches',
            f'{message} via API',
            request
        )
        
        return JsonResponse({
            'status': True,
            'message': message,
            'data': {
                'id': coach.id,
                'verified': coach.verified,
                'verification_status': admin_verification.status,
            }
        })
    except CoachProfile.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Coach not found'
        }, status=404)
    except json.JSONDecodeError:
        return JsonResponse({
            'status': False,
            'message': 'Invalid JSON data'
        }, status=400)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["DELETE", "POST"])
def api_coach_delete(request, coach_id):
    """
    Delete a coach (JSON API)
    DELETE /admin/api/coaches/<coach_id>/delete/
    """
    try:
        coach = CoachProfile.objects.select_related('user').get(id=coach_id)
        username = coach.user.username
        user = coach.user
        coach.delete()
        user.delete()
        
        log_admin_activity(
            request.admin_user, 'delete', 'coaches',
            f'Deleted coach {username} via API',
            request
        )
        
        return JsonResponse({
            'status': True,
            'message': f'Coach {username} deleted successfully'
        })
    except CoachProfile.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Coach not found'
        }, status=404)


# ==================== Courses API Endpoints ====================

@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_courses_list(request):
    """
    List all courses with filtering and pagination (JSON API)
    GET /admin/api/courses/
    Query params: search, coach_id, page, per_page
    """
    courses = Course.objects.select_related('coach__user').order_by('-id')
    
    # Filter by coach
    coach_id = request.GET.get('coach_id', '').strip()
    if coach_id:
        try:
            courses = courses.filter(coach_id=int(coach_id))
        except ValueError:
            pass
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(coach__user__username__icontains=search_query)
        )
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 10
    except ValueError:
        per_page = 10
    
    paginator = Paginator(courses, per_page)
    try:
        paginated_courses = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        paginated_courses = paginator.page(1)
    
    # Serialize courses
    courses_data = []
    for course in paginated_courses:
        courses_data.append({
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'price': float(course.price) if course.price else 0,
            'duration_minutes': course.duration_minutes,
            'coach': {
                'id': course.coach.id,
                'name': course.coach.user.get_full_name() or course.coach.user.username,
                'username': course.coach.user.username,
            } if course.coach else None,
            'image': course.image.url if course.image else None,
            'is_active': course.is_active if hasattr(course, 'is_active') else True,
        })
    
    log_admin_activity(request.admin_user, 'view', 'courses', 'Viewed courses via API', request)
    
    return JsonResponse({
        'status': True,
        'message': 'Courses retrieved successfully',
        'data': {
            'courses': courses_data,
            'pagination': {
                'current_page': paginated_courses.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'per_page': per_page,
                'has_next': paginated_courses.has_next(),
                'has_previous': paginated_courses.has_previous(),
            }
        }
    })


@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_course_detail(request, course_id):
    """
    Get single course details (JSON API)
    GET /admin/api/courses/<course_id>/
    """
    try:
        course = Course.objects.select_related('coach__user').get(id=course_id)
        
        # Get bookings count for this course
        bookings_count = Booking.objects.filter(course=course).count()
        
        course_data = {
            'id': course.id,
            'title': course.title,
            'description': course.description,
            'price': float(course.price) if course.price else 0,
            'duration_minutes': course.duration_minutes,
            'coach': {
                'id': course.coach.id,
                'name': course.coach.user.get_full_name() or course.coach.user.username,
                'username': course.coach.user.username,
                'email': course.coach.user.email,
            } if course.coach else None,
            'image': course.image.url if course.image else None,
            'is_active': course.is_active if hasattr(course, 'is_active') else True,
            'stats': {
                'bookings_count': bookings_count,
            }
        }
        
        return JsonResponse({
            'status': True,
            'message': 'Course retrieved successfully',
            'data': course_data
        })
    except Course.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Course not found'
        }, status=404)


@csrf_exempt
@api_admin_login_required
@require_http_methods(["DELETE", "POST"])
def api_course_delete(request, course_id):
    """
    Delete a course (JSON API)
    DELETE /admin/api/courses/<course_id>/delete/
    """
    try:
        course = Course.objects.get(id=course_id)
        title = course.title
        course.delete()
        
        log_admin_activity(
            request.admin_user, 'delete', 'courses',
            f'Deleted course {title} via API',
            request
        )
        
        return JsonResponse({
            'status': True,
            'message': f'Course "{title}" deleted successfully'
        })
    except Course.DoesNotExist:
        return JsonResponse({
            'status': False,
            'message': 'Course not found'
        }, status=404)


# ==================== Activity Logs API Endpoint ====================

@csrf_exempt
@api_admin_login_required
@require_http_methods(["GET"])
def api_activity_logs(request):
    """
    List admin activity logs (JSON API)
    GET /admin/api/logs/
    Query params: action, module, page, per_page
    """
    logs = AdminActivityLog.objects.select_related('admin_user').order_by('-timestamp')
    
    # Filter by action
    action_filter = request.GET.get('action', '').strip()
    if action_filter and action_filter != 'all':
        logs = logs.filter(action=action_filter)
    
    # Filter by module
    module_filter = request.GET.get('module', '').strip()
    if module_filter and module_filter != 'all':
        logs = logs.filter(module=module_filter)
    
    # Pagination
    page = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 50)
    try:
        per_page = int(per_page)
        if per_page not in [10, 25, 50, 100]:
            per_page = 50
    except ValueError:
        per_page = 50
    
    paginator = Paginator(logs, per_page)
    try:
        paginated_logs = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        paginated_logs = paginator.page(1)
    
    # Serialize logs
    logs_data = []
    for log in paginated_logs:
        logs_data.append({
            'id': log.id,
            'admin_user': {
                'id': log.admin_user.id,
                'username': log.admin_user.username,
            },
            'action': log.action,
            'module': log.module,
            'description': log.description,
            'ip_address': log.ip_address,
            'timestamp': log.timestamp.isoformat(),
        })
    
    return JsonResponse({
        'status': True,
        'message': 'Activity logs retrieved successfully',
        'data': {
            'logs': logs_data,
            'pagination': {
                'current_page': paginated_logs.number,
                'total_pages': paginator.num_pages,
                'total_items': paginator.count,
                'per_page': per_page,
                'has_next': paginated_logs.has_next(),
                'has_previous': paginated_logs.has_previous(),
            }
        }
    })


def admin_login_required(view_func):
    """Custom decorator to check if admin is logged in"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'admin_user_id' not in request.session:
            return redirect('admin_panel:login')
        
        try:
            admin_user = AdminUser.objects.get(id=request.session['admin_user_id'], is_active=True)
            request.admin_user = admin_user
        except AdminUser.DoesNotExist:
            del request.session['admin_user_id']
            return redirect('admin_panel:login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def log_admin_activity(admin_user, action, module, description, request=None):
    """Helper function to log admin activities"""
    ip_address = None
    user_agent = ''
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AdminActivityLog.objects.create(
        admin_user=admin_user,
        action=action,
        module=module,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent
    )


def paginate_queryset(request, queryset, per_page=10):
    """Utility function to paginate a queryset"""
    # Get per_page parameter, default to 10
    per_page_param = request.GET.get('per_page', per_page)
    try:
        per_page_param = int(per_page_param)
        if per_page_param not in [10, 25, 50]:
            per_page_param = per_page
    except (ValueError, TypeError):
        per_page_param = per_page
    
    paginator = Paginator(queryset, per_page_param)
    page = request.GET.get('page')
    
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)
    
    return items, per_page_param


@require_http_methods(["GET", "POST"])
def admin_login(request):
    """Admin login page"""
    # Check if already logged in
    if 'admin_user_id' in request.session:
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            admin_user = AdminUser.objects.get(username=username, is_active=True)
            if admin_user.check_password(password):
                # Set session
                request.session['admin_user_id'] = admin_user.id
                admin_user.last_login = timezone.now()
                admin_user.save()
                
                log_admin_activity(admin_user, 'login', 'auth', f'Admin logged in', request)
                messages.success(request, f'Welcome back, {admin_user.username}!')
                return redirect('admin_panel:dashboard')
            else:
                messages.error(request, 'Invalid credentials')
        except AdminUser.DoesNotExist:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'admin_panel/login.html')


@admin_login_required
def admin_logout(request):
    """Admin logout"""
    log_admin_activity(request.admin_user, 'logout', 'auth', f'Admin logged out', request)
    request.session.flush()
    messages.success(request, 'You have been logged out successfully')
    return redirect('admin_panel:login')


@admin_login_required
def dashboard(request):
    """Main admin dashboard"""
    # Get statistics
    total_users = UserProfile.objects.count()
    total_coaches = CoachProfile.objects.count()
    total_courses = Course.objects.count()
    total_bookings = Booking.objects.count()
    
    # Bookings by status
    pending_bookings = Booking.objects.filter(status='pending').count()
    confirmed_bookings = Booking.objects.filter(status='confirmed').count()
    done_bookings = Booking.objects.filter(status='done').count()
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related('user', 'course').order_by('-created_at')[:10]
    
    # Payment statistics
    total_revenue = Payment.objects.filter(status__in=['settlement', 'capture']).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Recent activity logs
    recent_logs = AdminActivityLog.objects.select_related('admin_user').order_by('-timestamp')[:10]
    
    log_admin_activity(request.admin_user, 'view', 'dashboard', 'Viewed admin dashboard', request)
    
    context = {
        'user': request.admin_user,
        'total_users': total_users,
        'total_coaches': total_coaches,
        'total_courses': total_courses,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'done_bookings': done_bookings,
        'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


@admin_login_required
def users_management(request):
    """User management page with search and pagination"""
    users = UserProfile.objects.select_related('user').order_by('-user__date_joined')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        users = users.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Pagination
    paginated_users, per_page = paginate_queryset(request, users, per_page=10)
    
    log_admin_activity(request.admin_user, 'view', 'users', 'Viewed users management', request)
    
    context = {
        'user': request.admin_user,
        'users': paginated_users,
        'search_query': search_query,
        'per_page': per_page,
        'paginator': paginated_users.paginator,
    }
    
    return render(request, 'admin_panel/users.html', context)


@admin_login_required
def coaches_management(request):
    """Coach management page with search and pagination"""
    coaches = CoachProfile.objects.select_related('user').prefetch_related('adminverification').order_by('-id')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        coaches = coaches.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query)
        )
    
    # Pagination
    paginated_coaches, per_page = paginate_queryset(request, coaches, per_page=10)
    
    log_admin_activity(request.admin_user, 'view', 'coaches', 'Viewed coaches management', request)
    
    context = {
        'user': request.admin_user,
        'coaches': paginated_coaches,
        'search_query': search_query,
        'per_page': per_page,
        'paginator': paginated_coaches.paginator,
    }
    
    return render(request, 'admin_panel/coaches.html', context)


@admin_login_required
def courses_management(request):
    """Course management page with search and pagination"""
    courses = Course.objects.select_related('coach').order_by('-id')
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        courses = courses.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(coach__user__username__icontains=search_query)
        )
    
    # Pagination
    paginated_courses, per_page = paginate_queryset(request, courses, per_page=10)
    
    log_admin_activity(request.admin_user, 'view', 'courses', 'Viewed courses management', request)
    
    context = {
        'user': request.admin_user,
        'courses': paginated_courses,
        'search_query': search_query,
        'per_page': per_page,
        'paginator': paginated_courses.paginator,
    }
    
    return render(request, 'admin_panel/courses.html', context)


@admin_login_required
def bookings_management(request):
    """Booking management page with search and pagination"""
    bookings = Booking.objects.select_related('user', 'course').order_by('-created_at')
    
    # Status filter
    status = request.GET.get('status', 'all')
    if status and status != 'all':
        bookings = bookings.filter(status=status)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        bookings = bookings.filter(
            Q(user__username__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(course__title__icontains=search_query) |
            Q(id__icontains=search_query)
        )
    
    # Pagination
    paginated_bookings, per_page = paginate_queryset(request, bookings, per_page=10)
    
    log_admin_activity(request.admin_user, 'view', 'bookings', 'Viewed bookings management', request)
    
    context = {
        'user': request.admin_user,
        'bookings': paginated_bookings,
        'search_query': search_query,
        'status': status,
        'per_page': per_page,
        'paginator': paginated_bookings.paginator,
    }
    
    return render(request, 'admin_panel/bookings.html', context)


@admin_login_required
def payments_management(request):
    """Payment management page with search and pagination"""
    # Base queryset
    payments = Payment.objects.select_related('booking__user', 'booking__course').order_by('-created_at')
    
    # Status filter
    status = request.GET.get('status', 'all')
    if status and status != 'all':
        payments = payments.filter(status=status)
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        payments = payments.filter(
            Q(order_id__icontains=search_query) |
            Q(booking__user__username__icontains=search_query) |
            Q(booking__user__email__icontains=search_query) |
            Q(booking__id__icontains=search_query)
        )
    
    # Pagination
    paginated_payments, per_page = paginate_queryset(request, payments, per_page=10)
    
    log_admin_activity(request.admin_user, 'view', 'payments', 'Viewed payments management', request)
    
    context = {
        'user': request.admin_user,
        'payments': paginated_payments,
        'search_query': search_query,
        'status': status,
        'per_page': per_page,
        'paginator': paginated_payments.paginator,
    }
    
    return render(request, 'admin_panel/payments.html', context)


@admin_login_required
def settings_management(request):
    """Settings management page"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            module = request.POST.get('module')
            key = request.POST.get('key')
            value = request.POST.get('value')
            
            AdminSettings.objects.create(
                module=module,
                key=key,
                value=value,
                updated_by=request.admin_user
            )
            log_admin_activity(request.admin_user, 'create', 'settings', f'Added setting {key}', request)
            messages.success(request, f'Setting {key} added successfully')
            
        elif action == 'update':
            setting_id = request.POST.get('setting_id')
            setting = get_object_or_404(AdminSettings, id=setting_id)
            old_value = setting.value
            setting.value = request.POST.get('value')
            setting.updated_by = request.admin_user
            setting.save()
            
            log_admin_activity(request.admin_user, 'update', 'settings', f'Updated {setting.key} from "{old_value}" to "{setting.value}"', request)
            messages.success(request, f'Setting {setting.key} updated successfully')
            
        elif action == 'delete':
            setting_id = request.POST.get('setting_id')
            setting = get_object_or_404(AdminSettings, id=setting_id)
            key = setting.key
            setting.delete()
            
            log_admin_activity(request.admin_user, 'delete', 'settings', f'Deleted setting {key}', request)
            messages.success(request, f'Setting {key} deleted successfully')
        
        return redirect('admin_panel:settings')
    
    # GET request - display settings
    settings = AdminSettings.objects.all().order_by('module', 'key')
    
    log_admin_activity(request.admin_user, 'view', 'settings', 'Viewed settings management', request)
    
    context = {
        'user': request.admin_user,
        'settings': settings,
    }
    
    return render(request, 'admin_panel/settings.html', context)


@admin_login_required
def activity_logs(request):
    """Activity logs page"""
    action_filter = request.GET.get('action', 'all')
    
    if action_filter != 'all':
        logs = AdminActivityLog.objects.filter(action=action_filter).select_related('admin_user').order_by('-timestamp')[:500]
    else:
        logs = AdminActivityLog.objects.select_related('admin_user').order_by('-timestamp')[:500]
    
    context = {
        'user': request.admin_user,
        'logs': logs,
    }
    
    return render(request, 'admin_panel/logs.html', context)


@admin_login_required
def change_password(request):
    """Change admin password"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Verify current password
        if not request.admin_user.check_password(old_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('admin_panel:change_password')
        
        # Verify new passwords match
        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match')
            return redirect('admin_panel:change_password')
        
        # Check password strength
        if len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('admin_panel:change_password')
        
        # Update password
        request.admin_user.set_password(new_password1)
        request.admin_user.save()
        
        log_admin_activity(request.admin_user, 'update', 'auth', 'Changed admin password', request)
        
        messages.success(request, 'Password changed successfully. Please login again.')
        return redirect('admin_panel:logout')
    
    context = {
        'user': request.admin_user,
    }
    return render(request, 'admin_panel/change_password.html', context)


# ==================== CRUD Operations ====================

@admin_login_required
def coach_verify(request, coach_id):
    """Toggle coach verified badge (independent from approval status)"""
    coach = get_object_or_404(CoachProfile, id=coach_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'verify':
            # Just toggle the verified badge - doesn't affect approval status
            coach.verified = True
            coach.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Added verified badge to coach {coach.user.username}', request)
            messages.success(request, f'Verified badge added to coach {coach.user.username}!')
            
        elif action == 'unverify':
            # Remove verified badge - doesn't affect approval status
            coach.verified = False
            coach.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Removed verified badge from coach {coach.user.username}', request)
            messages.success(request, f'Verified badge removed from coach {coach.user.username}.')
    
    return redirect('admin_panel:coaches')


@admin_login_required
def coach_verification_detail(request, coach_id):
    """View and manage coach approval status (ability to train on platform)"""
    coach = get_object_or_404(CoachProfile, id=coach_id)
    
    admin_verification, created = AdminVerification.objects.get_or_create(
        coach=coach,
        defaults={'certificate_url': '', 'status': 'pending'}
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            # Approve = Set status to approved AND give verified badge
            admin_verification.status = 'approved'
            admin_verification.notes = notes or f'Approved by {request.admin_user.username}'
            admin_verification.save()
            
            coach.verified = True
            coach.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Approved coach {coach.user.username} - verified badge granted', request)
            messages.success(request, f'Coach {coach.user.username} has been approved and verified badge granted!')
            
        elif action == 'reject':
            # Reject = Set status to rejected AND remove verified badge
            admin_verification.status = 'rejected'
            admin_verification.notes = notes or f'Rejected by {request.admin_user.username}'
            admin_verification.save()
            
            coach.verified = False
            coach.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Rejected coach {coach.user.username} - verified badge removed', request)
            messages.warning(request, f'Coach {coach.user.username} has been rejected and verified badge removed.')
            
        elif action == 'pending':
            # Set to pending review
            admin_verification.status = 'pending'
            admin_verification.notes = notes
            admin_verification.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Set approval status to pending for coach {coach.user.username}', request)
            messages.info(request, f'Coach {coach.user.username} approval status set to pending.')
        
        elif action == 'toggle_verified':
            # Toggle verified badge independently
            coach.verified = not coach.verified
            coach.save()
            
            badge_action = 'added' if coach.verified else 'removed'
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Verified badge {badge_action} for coach {coach.user.username}', request)
            messages.success(request, f'Verified badge {badge_action} for coach {coach.user.username}!')
        
        return redirect('admin_panel:coach_verification_detail', coach_id=coach_id)
    
    context = {
        'user': request.admin_user,
        'coach': coach,
        'admin_verification': admin_verification,
    }
    return render(request, 'admin_panel/coach_verification_detail.html', context)


@admin_login_required
def coach_delete(request, coach_id):
    """Delete a coach"""
    coach = get_object_or_404(CoachProfile, id=coach_id)
    
    if request.method == 'POST':
        username = coach.user.username
        user = coach.user
        coach.delete()
        user.delete()  # Also delete the associated user account
        
        log_admin_activity(request.admin_user, 'delete', 'coaches', f'Deleted coach {username}', request)
        messages.success(request, f'Coach {username} has been deleted successfully!')
        return redirect('admin_panel:coaches')
    
    context = {
        'user': request.admin_user,
        'coach': coach,
    }
    return render(request, 'admin_panel/coach_delete_confirm.html', context)


@admin_login_required
def user_delete(request, user_id):
    """Delete a user"""
    from django.contrib.auth.models import User
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        
        log_admin_activity(request.admin_user, 'delete', 'users', f'Deleted user {username}', request)
        messages.success(request, f'User {username} has been deleted successfully!')
        return redirect('admin_panel:users')
    
    context = {
        'user': request.admin_user,
        'user_obj': user_obj,
    }
    return render(request, 'admin_panel/user_delete_confirm.html', context)


@admin_login_required
def course_delete(request, course_id):
    """Delete a course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        course_name = course.title
        course.delete()
        
        log_admin_activity(request.admin_user, 'delete', 'courses', f'Deleted course {course_name}', request)
        messages.success(request, f'Course "{course_name}" has been deleted successfully!')
        return redirect('admin_panel:courses')
    
    context = {
        'user': request.admin_user,
        'course': course,
    }
    return render(request, 'admin_panel/course_delete_confirm.html', context)


@admin_login_required
def booking_update_status(request, booking_id):
    """Update booking status"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = booking.status
        
        if new_status in dict(Booking.STATUS_CHOICES):
            booking.status = new_status
            booking.save()
            
            log_admin_activity(request.admin_user, 'update', 'bookings', 
                             f'Updated booking #{booking.id} status from {old_status} to {new_status}', request)
            messages.success(request, f'Booking status updated to {new_status}!')
        else:
            messages.error(request, 'Invalid status!')
    
    return redirect('admin_panel:bookings')


@admin_login_required
def booking_delete(request, booking_id):
    """Delete a booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        booking_info = f"#{booking.id} - {booking.user.username} - {booking.course.title}"
        booking.delete()
        
        log_admin_activity(request.admin_user, 'delete', 'bookings', f'Deleted booking {booking_info}', request)
        messages.success(request, f'Booking has been deleted successfully!')
        return redirect('admin_panel:bookings')
    
    context = {
        'user': request.admin_user,
        'booking': booking,
    }
    return render(request, 'admin_panel/booking_delete_confirm.html', context)


@admin_login_required
def payment_update_status(request, payment_id):
    """Update payment status"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = payment.status
        
        payment.status = new_status
        payment.save()
        
        log_admin_activity(request.admin_user, 'update', 'payments', 
                         f'Updated payment {payment.order_id} status from {old_status} to {new_status}', request)
        messages.success(request, f'Payment status updated to {new_status}!')
    
    return redirect('admin_panel:payments')
