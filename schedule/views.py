from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime
import json

from schedule.models import CoachAvailability
from user_profile.models import CoachProfile


@login_required
@require_http_methods(["POST"])
def api_availability_upsert(request):
    """
    Upsert coach availability for a specific date.
    Replaces all existing ranges for that date with new ones.
    
    POST /schedule/api/availability/upsert/
    Body: {
        "date": "YYYY-MM-DD",
        "ranges": [
            {"start": "HH:MM", "end": "HH:MM"},
            ...
        ]
    }
    """
    try:
        # Verify user is a coach
        coach = get_object_or_404(CoachProfile, user=request.user)
        
        # Parse request body
        data = json.loads(request.body)
        date_str = data.get('date')
        ranges = data.get('ranges', [])
        
        if not date_str:
            return JsonResponse({'error': 'Date is required'}, status=400)
        
        # Parse date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        # Validate ranges
        if not ranges or not isinstance(ranges, list):
            return JsonResponse({'error': 'At least one time range is required'}, status=400)
        
        # Parse and validate time ranges
        parsed_ranges = []
        for idx, range_data in enumerate(ranges):
            try:
                start_str = range_data.get('start')
                end_str = range_data.get('end')
                
                if not start_str or not end_str:
                    return JsonResponse({
                        'error': f'Range {idx + 1}: start and end times are required'
                    }, status=400)
                
                start_time = datetime.strptime(start_str, '%H:%M').time()
                end_time = datetime.strptime(end_str, '%H:%M').time()
                
                if end_time <= start_time:
                    return JsonResponse({
                        'error': f'Range {idx + 1}: end time must be after start time'
                    }, status=400)
                
                parsed_ranges.append((start_time, end_time))
                
            except ValueError:
                return JsonResponse({
                    'error': f'Range {idx + 1}: invalid time format. Use HH:MM'
                }, status=400)
        
        # Upsert: Delete existing ranges for this date, then create new ones
        with transaction.atomic():
            # Delete existing availabilities for this coach and date
            CoachAvailability.objects.filter(
                coach=coach,
                date=target_date
            ).delete()
            
            # Bulk create new availabilities
            availabilities = [
                CoachAvailability(
                    coach=coach,
                    date=target_date,
                    start_time=start_time,
                    end_time=end_time
                )
                for start_time, end_time in parsed_ranges
            ]
            
            CoachAvailability.objects.bulk_create(availabilities)
        
        return JsonResponse({
            'success': True,
            'message': f'{len(parsed_ranges)} time range(s) saved for {date_str}',
            'date': date_str,
            'count': len(parsed_ranges)
        })
        
    except CoachProfile.DoesNotExist:
        return JsonResponse({'error': 'You must be a coach to set availability'}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["GET"])
def api_availability_list(request):
    """
    Get coach availability for a specific date.
    
    GET /schedule/api/availability/?date=YYYY-MM-DD
    Returns: {
        "date": "YYYY-MM-DD",
        "ranges": [
            {"start": "HH:MM", "end": "HH:MM", "id": 123},
            ...
        ]
    }
    """
    try:
        # Verify user is a coach
        coach = get_object_or_404(CoachProfile, user=request.user)
        
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'error': 'Date parameter is required'}, status=400)
        
        # Parse date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        # Get availabilities for this date
        availabilities = CoachAvailability.objects.filter(
            coach=coach,
            date=target_date
        ).order_by('start_time')
        
        ranges = [
            {
                'id': avail.id,
                'start': avail.start_time.strftime('%H:%M'),
                'end': avail.end_time.strftime('%H:%M')
            }
            for avail in availabilities
        ]
        
        return JsonResponse({
            'date': date_str,
            'ranges': ranges,
            'count': len(ranges)
        })
        
    except CoachProfile.DoesNotExist:
        return JsonResponse({'error': 'You must be a coach'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def api_availability_delete(request):
    """
    Delete all coach availability for a specific date.
    
    DELETE /schedule/api/availability/?date=YYYY-MM-DD
    """
    try:
        # Verify user is a coach
        coach = get_object_or_404(CoachProfile, user=request.user)
        
        date_str = request.GET.get('date')
        if not date_str:
            return JsonResponse({'error': 'Date parameter is required'}, status=400)
        
        # Parse date
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
        
        # Delete availabilities for this date
        deleted_count, _ = CoachAvailability.objects.filter(
            coach=coach,
            date=target_date
        ).delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Deleted {deleted_count} time range(s) for {date_str}',
            'deleted_count': deleted_count
        })
        
    except CoachProfile.DoesNotExist:
        return JsonResponse({'error': 'You must be a coach'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

