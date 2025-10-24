from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.db import transaction
from .models import Booking
from user_profile.models import CoachProfile
from schedule.models import ScheduleSlot
from courses_and_coach.models import Course
from booking.services.availability import get_available_start_times
from datetime import datetime, timedelta
import calendar, pytz, json

@login_required
def get_available_dates(request, coach_id):
    """
    Return dates yang available untuk coach dalam 1 bulan
    Berdasarkan tanggal spesifik di ScheduleSlot
    """
    try:
        coach = get_object_or_404(CoachProfile, id=coach_id)
        
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        
        # Get all schedule slots untuk bulan ini yang available
        schedule_slots = ScheduleSlot.objects.filter(
            coach=coach,
            date__year=year,
            date__month=month,
            date__gte=datetime.now().date(),  # Only future dates
            is_available=True
        ).values_list('date', flat=True).distinct()
        
        available_dates = []
        
        for date in schedule_slots:
            # Check if ada slot yang belum di-booking penuh
            slots_count = ScheduleSlot.objects.filter(
                coach=coach,
                date=date,
                is_available=True
            ).count()
            
            booked_count = Booking.objects.filter(
                coach=coach,
                date=date,
                status__in=['pending', 'confirmed']
            ).count()
            
            # Jika masih ada slot available
            if booked_count < slots_count:
                available_dates.append({
                    'date': date.isoformat(),
                    'day': date.day,
                    'available': True
                })
        
        return JsonResponse({
            'available_dates': available_dates,
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month]
        })
    
    except Exception as e:
        print(f"Error in get_available_dates: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'error': str(e),
            'available_dates': [],
            'year': datetime.now().year,
            'month': datetime.now().month,
            'month_name': calendar.month_name[datetime.now().month]
        }, status=500)


@login_required
def get_available_times(request, coach_id):
    """
    Return available time slots untuk coach pada date tertentu
    """
    try:
        coach = get_object_or_404(CoachProfile, id=coach_id)
        date_str = request.GET.get('date')
        
        if not date_str:
            return JsonResponse({'error': 'Date required'}, status=400)
        
        date = datetime.fromisoformat(date_str).date()
        
        # Get all slots untuk tanggal ini
        slots = ScheduleSlot.objects.filter(
            coach=coach,
            date=date,
            is_available=True
        ).order_by('start_time')
        
        available_times = []
        
        for slot in slots:
            # Check if slot sudah di-booking
            is_booked = Booking.objects.filter(
                coach=coach,
                schedule=slot,
                date=date,
                status__in=['pending', 'confirmed']
            ).exists()
            
            if not is_booked:
                available_times.append({
                    'slot_id': slot.id,
                    'start_time': slot.start_time.strftime('%H:%M'),
                    'end_time': slot.end_time.strftime('%H:%M'),
                    'display': f"{slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"
                })
        
        return JsonResponse({
            'available_times': available_times,
            'date': date_str,
            'day_name': date.strftime('%A')
        })
    
    except Exception as e:
        print(f"Error in get_available_times: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'error': str(e),
            'available_times': []
        }, status=500)


@login_required
@require_POST
def create_booking(request, course_id):
    """
    Create booking setelah user pilih date dan time
    """
    try:
        course = get_object_or_404(Course, id=course_id)
        
        data = json.loads(request.body)
        schedule_id = data.get('schedule_id')
        date_str = data.get('date')
        
        if not schedule_id or not date_str:
            return JsonResponse({
                'success': False,
                'message': 'Schedule and date required'
            }, status=400)
        
        schedule = get_object_or_404(ScheduleSlot, id=schedule_id)
        date = datetime.fromisoformat(date_str).date()
        
        # Validasi schedule milik coach yang benar
        if schedule.coach != course.coach:
            return JsonResponse({
                'success': False,
                'message': 'Invalid schedule for this coach'
            }, status=400)
        
        # Validasi date sesuai dengan schedule
        if schedule.date != date:
            return JsonResponse({
                'success': False,
                'message': 'Date mismatch with schedule'
            }, status=400)
        
        # Check double booking
        existing = Booking.objects.filter(
            coach=course.coach,
            schedule=schedule,
            date=date,
            status__in=['pending', 'confirmed']
        ).exists()
        
        if existing:
            return JsonResponse({
                'success': False,
                'message': 'This time slot is already booked'
            }, status=400)
        
        # Create booking
        booking = Booking.objects.create(
            user=request.user,
            coach=course.coach,
            course=course,
            schedule=schedule,
            date=date,
            status='pending'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Booking created successfully',
            'booking_id': booking.id,
            'redirect_url': f'/payment/booking/{booking.id}/'
        })
        
    except Exception as e:
        print(f"Error in create_booking: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ========== NEW API ENDPOINTS FOR AVAILABILITY SYSTEM ==========

@login_required
@require_http_methods(["GET"])
def api_course_start_times(request, course_id):
    """
    Get available start times for a course on a specific date.
    
    GET /booking/api/course/<course_id>/start-times/?date=YYYY-MM-DD
    Returns: {
        "date": "YYYY-MM-DD",
        "start_times": ["09:00", "09:30", "10:00", ...],
        "course_duration": 60
    }
    """
    try:
        course = get_object_or_404(Course, id=course_id)
        date_str = request.GET.get('date')
        
        if not date_str:
            return JsonResponse({'error': 'Date parameter is required'}, status=400)
        
        # Parse date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        # Get available start times using the service function
        start_times = get_available_start_times(
            coach=course.coach,
            course=course,
            target_date=target_date,
            step_minutes=30  # 30-minute intervals
        )
        
        return JsonResponse({
            'date': date_str,
            'start_times': start_times,
            'course_duration': course.duration,
            'course_title': course.title
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def api_booking_create(request, course_id):
    """Create new booking with overlap detection"""
    try:
        data = json.loads(request.body)
        date_str = data.get('date')  # "2025-10-24"
        start_time_str = data.get('start_time')  # "13:27"
        
        if not date_str or not start_time_str:
            return JsonResponse({'success': False, 'error': 'Date and start time required'}, status=400)
        
        course = get_object_or_404(Course, id=course_id)
        coach = course.coach
        
        # ✅ Parse dengan timezone awareness
        # Combine date + time
        naive_datetime = datetime.strptime(f"{date_str} {start_time_str}", "%Y-%m-%d %H:%M")
        
        # Make timezone-aware (using Jakarta timezone UTC+7)
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        start_datetime = jakarta_tz.localize(naive_datetime)
        
        # Calculate end datetime
        end_datetime = start_datetime + timedelta(minutes=course.duration)
        
        # Check overlap with transaction
        with transaction.atomic():
            # Lock existing bookings
            overlapping = Booking.objects.select_for_update().filter(
                coach=coach,
                status__in=['pending', 'paid', 'confirmed'],
                start_datetime__lt=end_datetime,
                end_datetime__gt=start_datetime
            )
            
            if overlapping.exists():
                return JsonResponse({
                    'success': False,
                    'error': 'Time slot not available. Please choose another time.'
                }, status=409)
            
            # Create booking
            booking = Booking.objects.create(
                user=request.user,
                coach=coach,
                course=course,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                status='pending'
            )
        
        return JsonResponse({
            'success': True,
            'booking_id': booking.id,
            'message': 'Booking created successfully'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_booking_list(request):
    """
    Get bookings for the logged-in user or coach.
    
    GET /booking/api/bookings/?role=user&status=pending
    Query params:
        - role: 'user' or 'coach' (default: 'user')
        - status: filter by status (optional)
    """
    try:
        role = request.GET.get('role', 'user')
        status_filter = request.GET.get('status')
        
        if role == 'coach':
            # Get coach bookings
            try:
                coach = CoachProfile.objects.get(user=request.user)
                bookings_qs = Booking.objects.filter(coach=coach)
            except CoachProfile.DoesNotExist:
                return JsonResponse({'error': 'You are not a coach'}, status=403)
        else:
            # Get user bookings
            bookings_qs = Booking.objects.filter(user=request.user)
        
        # Apply status filter if provided
        if status_filter:
            bookings_qs = bookings_qs.filter(status=status_filter)
        
        # Select related for optimization
        bookings_qs = bookings_qs.select_related(
            'user', 'coach__user', 'course'
        ).order_by('-created_at')
        
        bookings_data = [
            {
                'id': booking.id,
                'user_name': booking.user.get_full_name() or booking.user.username,
                'coach_name': booking.coach.user.get_full_name(),
                'course_title': booking.course.title,
                'start_datetime': booking.start_datetime.isoformat(),
                'end_datetime': booking.end_datetime.isoformat(),
                'date': booking.date.isoformat(),
                'start_time': booking.start_time.strftime('%H:%M'),
                'end_time': booking.end_time.strftime('%H:%M'),
                'status': booking.status,
                'created_at': booking.created_at.isoformat()
            }
            for booking in bookings_qs
        ]
        
        return JsonResponse({
            'bookings': bookings_data,
            'count': len(bookings_data)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_booking_update_status(request, booking_id):
    """
    Update booking status (coach only).
    
    POST /booking/api/booking/<booking_id>/status/
    Body: {
        "status": "confirmed" | "done" | "canceled"
    }
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        
        # Verify user is the coach of this booking
        try:
            coach = CoachProfile.objects.get(user=request.user)
            if booking.coach != coach:
                return JsonResponse({
                    'error': 'You are not authorized to update this booking'
                }, status=403)
        except CoachProfile.DoesNotExist:
            return JsonResponse({'error': 'You are not a coach'}, status=403)
        
        # Parse request body
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['paid', 'confirmed', 'done', 'canceled']:
            return JsonResponse({
                'error': 'Invalid status. Must be: paid, confirmed, done, or canceled'
            }, status=400)
        
        # Update status
        booking.status = new_status
        booking.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Booking status updated to {new_status}',
            'booking_id': booking.id,
            'status': booking.status
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_booking_cancel(request, booking_id):
    """
    Cancel a booking (user can cancel own pending booking, coach can cancel any).
    
    POST /booking/api/booking/<booking_id>/cancel/
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        
        # Check authorization
        is_owner = booking.user == request.user
        is_coach = False
        
        try:
            coach = CoachProfile.objects.get(user=request.user)
            is_coach = booking.coach == coach
        except CoachProfile.DoesNotExist:
            pass
        
        if not (is_owner or is_coach):
            return JsonResponse({
                'error': 'You are not authorized to cancel this booking'
            }, status=403)
        
        # User can only cancel pending bookings
        if is_owner and not is_coach and booking.status != 'pending':
            return JsonResponse({
                'error': 'You can only cancel pending bookings'
            }, status=400)
        
        # Cancel the booking
        booking.status = 'canceled'
        booking.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Booking cancelled successfully',
            'booking_id': booking.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_POST
def api_booking_mark_as_paid(request, booking_id):
    """
    Mark booking as paid (after payment completion).
    This endpoint should be called by the payment module.
    
    POST /booking/api/booking/<booking_id>/mark-paid/
    Body: {
        "payment_id": "optional_payment_reference",
        "payment_method": "optional_payment_method"
    }
    """
    try:
        booking = get_object_or_404(Booking, id=booking_id)
        
        # Verify user owns this booking
        if booking.user != request.user:
            return JsonResponse({
                'error': 'You are not authorized to update this booking'
            }, status=403)
        
        # Only pending bookings can be marked as paid
        if booking.status != 'pending':
            return JsonResponse({
                'error': f'Only pending bookings can be marked as paid. Current status: {booking.status}'
            }, status=400)
        
        # Parse optional payment info
        data = json.loads(request.body) if request.body else {}
        payment_id = data.get('payment_id')
        payment_method = data.get('payment_method')
        
        # Update status to paid
        booking.status = 'paid'
        booking.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Booking marked as paid successfully',
            'booking_id': booking.id,
            'status': booking.status,
            'payment_id': payment_id,
            'payment_method': payment_method
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ========== COMPATIBILITY ENDPOINTS FOR OLD BOOKING SYSTEM ==========

@login_required
@require_http_methods(["GET"])
def api_coach_available_dates_legacy(request, coach_id):
    """
    Legacy endpoint for old booking UI.
    Returns available dates based on CoachAvailability.
    
    GET /api/coach/<coach_id>/available-dates/?year=YYYY&month=MM
    """
    try:
        coach = get_object_or_404(CoachProfile, id=coach_id)
        
        year = int(request.GET.get('year', datetime.now().year))
        month = int(request.GET.get('month', datetime.now().month))
        
        # Get all availabilities for this coach in the specified month
        from schedule.models import CoachAvailability
        
        availabilities = CoachAvailability.objects.filter(
            coach=coach,
            date__year=year,
            date__month=month,
            date__gte=datetime.now().date()
        ).values_list('date', flat=True).distinct()
        
        available_dates = []
        for date in availabilities:
            available_dates.append({
                'date': date.isoformat(),
                'day': date.day,
                'available': True
            })
        
        return JsonResponse({
            'available_dates': available_dates,
            'year': year,
            'month': month,
            'month_name': calendar.month_name[month]
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'available_dates': [],
            'year': datetime.now().year,
            'month': datetime.now().month,
            'month_name': calendar.month_name[datetime.now().month]
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_coach_available_times_legacy(request, coach_id):
    """
    Legacy endpoint for old booking UI.
    Returns available time slots for a specific date.
    
    GET /api/coach/<coach_id>/available-times/?date=YYYY-MM-DD&course_id=123
    """
    try:
        coach = get_object_or_404(CoachProfile, id=coach_id)
        date_str = request.GET.get('date')
        course_id = request.GET.get('course_id')
        
        if not date_str:
            return JsonResponse({'error': 'Date required'}, status=400)
        
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get course to determine duration
        if course_id:
            course = get_object_or_404(Course, id=course_id, coach=coach)
        else:
            # Get first course if not specified
            course = coach.courses.first()
            if not course:
                return JsonResponse({
                    'error': 'Coach has no courses',
                    'available_times': []
                }, status=400)
        
        # Use the new availability service
        start_times = get_available_start_times(
            coach=coach,
            course=course,
            target_date=target_date,
            step_minutes=30
        )
        
        # Format for old UI
        available_times = []
        for start_time_str in start_times:
            available_times.append({
                'start_time': start_time_str,
                'display': start_time_str,
                'available': True
            })
        print(available_times)
        return JsonResponse({
            'available_times': available_times,
            'date': date_str,
            'day_name': target_date.strftime('%A')
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'available_times': []
        }, status=500)


@login_required
def booking_confirmation(request, course_id):
    """
    Halaman konfirmasi booking sebelum payment
    User sudah pilih tanggal dan waktu dari calendar
    """
    course = get_object_or_404(Course, id=course_id)
    
    # Get date and time from query parameters
    booking_date = request.GET.get('date')
    booking_time = request.GET.get('time')
    
    context = {
        'course': course,
        'booking_date': booking_date,
        'booking_time': booking_time,
    }
    
    return render(request, 'booking/confirmation.html', context)


@login_required
def booking_success(request, booking_id):
    """
    Halaman success setelah booking berhasil dibuat
    Menampilkan detail booking dan next steps
    """
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    context = {
        'booking': booking,
    }
    
    return render(request, 'booking/success.html', context)
