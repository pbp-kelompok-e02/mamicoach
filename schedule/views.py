from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.core.exceptions import ValidationError
from datetime import datetime
import json

from schedule.models import CoachAvailability
from user_profile.models import CoachProfile
from booking.services.availability import merge_intervals


@csrf_exempt
@login_required
@require_http_methods(["POST"])
def api_availability_upsert(request):
    """
    Upsert coach availability for a specific date with auto-merge.
    
    Behavior:
    - REPLACE mode: Deletes all existing intervals for the date, then saves new ones
    - Auto-merge: New intervals are merged if they overlap/adjacent
    - Returns merged intervals for UI preview
    
    POST /schedule/api/availability/upsert/
    Body: {
        "date": "YYYY-MM-DD",
        "ranges": [
            {"start": "HH:MM", "end": "HH:MM"},
            ...
        ],
        "mode": "replace"  // Optional: "replace" (default) or "merge"
    }
    
    Response: {
        "success": true,
        "message": "...",
        "date": "YYYY-MM-DD",
        "merged_intervals": [
            {"start": "HH:MM", "end": "HH:MM"},
            ...
        ],
        "original_count": 3,
        "merged_count": 2
    }
    """
    try:
        # Verify user is a coach
        coach = get_object_or_404(CoachProfile, user=request.user)
        
        # Parse request body
        data = json.loads(request.body)
        date_str = data.get('date')
        ranges = data.get('ranges', [])
        mode = data.get('mode', 'replace')  # Options: 'replace', 'merge', 'add'
        
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
        
        # Step 1: Get existing intervals based on mode
        if mode == 'merge':
            # Merge mode: combine with existing intervals
            existing_availabilities = CoachAvailability.objects.filter(
                coach=coach,
                date=target_date
            ).values_list('start_time', 'end_time')
            existing_intervals = list(existing_availabilities)
        elif mode == 'add':
            # Add mode: insert without merging (keep existing separate)
            existing_intervals = []
        else:
            # Replace mode: ignore existing intervals (will delete all later)
            existing_intervals = []
        
        # Step 2: Parse and validate new ranges
        new_intervals = []
        range_statuses = []  # Store status for each range
        for idx, range_data in enumerate(ranges):
            try:
                start_str = range_data.get('start')
                end_str = range_data.get('end')
                status = range_data.get('status', 'active')  # Default to 'active'
                
                if not start_str or not end_str:
                    return JsonResponse({
                        'error': f'Range {idx + 1}: start and end times are required'
                    }, status=400)
                
                start_time = datetime.strptime(start_str, '%H:%M').time()
                end_time = datetime.strptime(end_str, '%H:%M').time()
                
                # Validation: end_time must be after start_time
                if end_time <= start_time:
                    return JsonResponse({
                        'error': f'Range {idx + 1}: end time ({end_str}) must be after start time ({start_str})'
                    }, status=400)
                
                new_intervals.append((start_time, end_time))
                range_statuses.append(status)
                
            except ValueError:
                return JsonResponse({
                    'error': f'Range {idx + 1}: invalid time format. Use HH:MM (24-hour)'
                }, status=400)
        
        # Step 3: Determine intervals to process based on mode
        if mode == 'merge':
            # Merge mode: combine existing + new
            all_intervals = existing_intervals + new_intervals
            original_count = len(all_intervals)
        else:
            # Replace mode: only use new intervals
            all_intervals = new_intervals
            original_count = len(new_intervals)
        
        # Step 4: Auto-merge overlapping/adjacent intervals within new set
        merged = merge_intervals(all_intervals)
        merged_count = len(merged)
        
        # Step 5: Upsert based on mode
        with transaction.atomic():
            if mode == 'add':
                # Add mode: Just insert new intervals without deleting existing
                availabilities = [
                    CoachAvailability(
                        coach=coach,
                        date=target_date,
                        start_time=start_time,
                        end_time=end_time,
                        status=range_statuses[i] if i < len(range_statuses) else 'active'
                    )
                    for i, (start_time, end_time) in enumerate(new_intervals)
                ]
                CoachAvailability.objects.bulk_create(availabilities)
                
            elif mode == 'merge':
                # Merge mode: Delete all and create merged intervals
                # Note: When merging, all intervals get the status from the first range
                CoachAvailability.objects.filter(
                    coach=coach,
                    date=target_date
                ).delete()
                
                default_status = range_statuses[0] if range_statuses else 'active'
                availabilities = [
                    CoachAvailability(
                        coach=coach,
                        date=target_date,
                        start_time=start_time,
                        end_time=end_time,
                        status=default_status
                    )
                    for start_time, end_time in merged
                ]
                CoachAvailability.objects.bulk_create(availabilities)
                
            else:  # replace mode
                # Replace mode: Delete all and create new intervals
                CoachAvailability.objects.filter(
                    coach=coach,
                    date=target_date
                ).delete()
                
                availabilities = [
                    CoachAvailability(
                        coach=coach,
                        date=target_date,
                        start_time=start_time,
                        end_time=end_time,
                        status=range_statuses[i] if i < len(range_statuses) else 'active'
                    )
                    for i, (start_time, end_time) in enumerate(merged)
                ]
                CoachAvailability.objects.bulk_create(availabilities)
        
        # Step 6: Format response with merged intervals
        merged_intervals_response = [
            {
                'start': start_time.strftime('%H:%M'),
                'end': end_time.strftime('%H:%M')
            }
            for start_time, end_time in merged
        ]
        
        # Build message based on mode
        if mode == 'merge':
            message = f'Availability updated for {date_str}. {original_count} interval(s) merged into {merged_count}.'
        else:
            if original_count == merged_count:
                message = f'Availability updated for {date_str}. {merged_count} interval(s) saved.'
            else:
                message = f'Availability updated for {date_str}. {original_count} interval(s) merged into {merged_count}.'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'date': date_str,
            'merged_intervals': merged_intervals_response,
            'original_count': original_count,
            'merged_count': merged_count
        })
        
    except CoachProfile.DoesNotExist:
        return JsonResponse({'error': 'You must be a coach to set availability'}, status=403)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["GET"])
def api_availability_list(request):
    """
    Get coach availability for a specific date or date range.
    
    GET /schedule/api/availability/?date=YYYY-MM-DD  (single date)
    GET /schedule/api/availability/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD  (date range)
    
    Returns: {
        "availabilities": [
            {
                "id": 123,
                "date": "YYYY-MM-DD",
                "start_time": "HH:MM",
                "end_time": "HH:MM",
                "status": "active"
            },
            ...
        ]
    }
    """
    try:
        # Verify user is a coach
        coach = get_object_or_404(CoachProfile, user=request.user)
        
        # Check if single date or date range
        date_str = request.GET.get('date')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        if date_str:
            # Single date query
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
            
            availabilities = CoachAvailability.objects.filter(
                coach=coach,
                date=target_date
            ).order_by('start_time')
            
        elif start_date_str and end_date_str:
            # Date range query
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
            
            availabilities = CoachAvailability.objects.filter(
                coach=coach,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date', 'start_time')
            
        else:
            return JsonResponse({
                'error': 'Either date or start_date+end_date parameters are required'
            }, status=400)
        
        # Format response
        result = [
            {
                'id': avail.id,
                'coach_id': avail.coach.id,
                'date': avail.date.strftime('%Y-%m-%d'),
                'start_time': avail.start_time.strftime('%H:%M'),
                'end_time': avail.end_time.strftime('%H:%M'),
                'status': avail.status,
                'created_at': avail.created_at.isoformat() if hasattr(avail, 'created_at') else None,
                'updated_at': avail.updated_at.isoformat() if hasattr(avail, 'updated_at') else None,
            }
            for avail in availabilities
        ]
        
        return JsonResponse({
            'availabilities': result,
            'count': len(result)
        })
        
    except CoachProfile.DoesNotExist:
        return JsonResponse({'error': 'You must be a coach'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["DELETE", "POST"])  # Allow both DELETE and POST for mobile compatibility
def api_availability_delete(request):
    """
    Delete coach availability by ID or by date.
    
    DELETE /schedule/api/availability/?id=<id>  (delete single availability by ID)
    DELETE /schedule/api/availability/?date=YYYY-MM-DD  (delete all for date)
    """
    try:
        # Verify user is a coach
        coach = get_object_or_404(CoachProfile, user=request.user)
        
        # Check if deleting by ID or by date
        availability_id = request.GET.get('id')
        date_str = request.GET.get('date')
        
        if availability_id:
            # Delete by ID
            try:
                availability = CoachAvailability.objects.get(
                    id=availability_id,
                    coach=coach
                )
                availability.delete()
                return JsonResponse({
                    'success': True,
                    'message': f'Deleted availability #{availability_id}'
                })
            except CoachAvailability.DoesNotExist:
                return JsonResponse({
                    'error': 'Availability not found or you do not have permission'
                }, status=404)
                
        elif date_str:
            # Delete by date
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
        else:
            return JsonResponse({
                'error': 'Either id or date parameter is required'
            }, status=400)
        
    except CoachProfile.DoesNotExist:
        return JsonResponse({'error': 'You must be a coach'}, status=403)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

