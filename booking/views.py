from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Booking
from user_profile.models import CoachProfile
from schedule.models import ScheduleSlot
from courses_and_coach.models import Course
from datetime import datetime
import calendar
import json

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
            'redirect_url': f'/booking/payment/{booking.id}/'
        })
        
    except Exception as e:
        print(f"Error in create_booking: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)