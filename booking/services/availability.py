"""
Availability Service - Helper functions for calculating available time slots.

This module provides utilities for:
- Merging overlapping time intervals
- Subtracting busy intervals from available intervals
- Enumerating possible start times based on course duration
- Finding available start times for a coach on a specific date
"""

from datetime import datetime, timedelta, time as dt_time, date as dt_date
from typing import List, Tuple
from django.db.models import Q


def merge_intervals(intervals: List[Tuple[dt_time, dt_time]]) -> List[Tuple[dt_time, dt_time]]:
    """
    Merge overlapping time intervals.
    
    Args:
        intervals: List of (start_time, end_time) tuples
        
    Returns:
        List of merged non-overlapping intervals, sorted by start time
        
    Example:
        Input: [(09:00, 11:00), (10:30, 12:00), (14:00, 15:00)]
        Output: [(09:00, 12:00), (14:00, 15:00)]
    """
    if not intervals:
        return []
    
    # Convert times to minutes for easier comparison
    def time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    def minutes_to_time(m):
        return dt_time(hour=m // 60, minute=m % 60)
    
    # Sort intervals by start time
    sorted_intervals = sorted(intervals, key=lambda x: time_to_minutes(x[0]))
    
    merged = []
    current_start, current_end = sorted_intervals[0]
    current_start_min = time_to_minutes(current_start)
    current_end_min = time_to_minutes(current_end)
    
    for start, end in sorted_intervals[1:]:
        start_min = time_to_minutes(start)
        end_min = time_to_minutes(end)
        
        # Check if intervals overlap or touch
        if start_min <= current_end_min:
            # Merge intervals
            current_end_min = max(current_end_min, end_min)
        else:
            # Add completed interval and start new one
            merged.append((
                minutes_to_time(current_start_min),
                minutes_to_time(current_end_min)
            ))
            current_start_min = start_min
            current_end_min = end_min
    
    # Add last interval
    merged.append((
        minutes_to_time(current_start_min),
        minutes_to_time(current_end_min)
    ))
    
    return merged


def subtract_busy(available_intervals: List[Tuple[dt_time, dt_time]], 
                  busy_intervals: List[Tuple[dt_time, dt_time]]) -> List[Tuple[dt_time, dt_time]]:
    """
    Subtract busy intervals from available intervals to get free intervals.
    
    Args:
        available_intervals: List of (start_time, end_time) tuples representing availability
        busy_intervals: List of (start_time, end_time) tuples representing bookings
        
    Returns:
        List of free intervals
        
    Example:
        Available: [(09:00, 15:00)]
        Busy: [(10:00, 11:00), (13:00, 14:00)]
        Result: [(09:00, 10:00), (11:00, 13:00), (14:00, 15:00)]
    """
    if not available_intervals:
        return []
    
    if not busy_intervals:
        return available_intervals
    
    def time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    def minutes_to_time(m):
        return dt_time(hour=m // 60, minute=m % 60)
    
    # Merge overlapping busy intervals first
    busy_merged = merge_intervals(busy_intervals)
    
    # Process each available interval
    free_intervals = []
    
    for avail_start, avail_end in available_intervals:
        avail_start_min = time_to_minutes(avail_start)
        avail_end_min = time_to_minutes(avail_end)
        
        current_free_start = avail_start_min
        
        for busy_start, busy_end in busy_merged:
            busy_start_min = time_to_minutes(busy_start)
            busy_end_min = time_to_minutes(busy_end)
            
            # Check if busy interval overlaps with current available interval
            if busy_end_min <= avail_start_min or busy_start_min >= avail_end_min:
                # No overlap, skip
                continue
            
            # If there's free time before busy interval
            if current_free_start < busy_start_min:
                free_intervals.append((
                    minutes_to_time(current_free_start),
                    minutes_to_time(min(busy_start_min, avail_end_min))
                ))
            
            # Move current free start to after busy interval
            current_free_start = max(current_free_start, busy_end_min)
        
        # Add remaining free time after all busy intervals
        if current_free_start < avail_end_min:
            free_intervals.append((
                minutes_to_time(current_free_start),
                minutes_to_time(avail_end_min)
            ))
    
    return free_intervals


def enumerate_starts(free_intervals: List[Tuple[dt_time, dt_time]], 
                     duration_minutes: int, 
                     step_minutes: int = 30) -> List[dt_time]:
    """
    Enumerate possible start times within free intervals.
    
    Args:
        free_intervals: List of (start_time, end_time) tuples
        duration_minutes: Duration of the course in minutes
        step_minutes: Step size for enumerating start times (default: 30)
        
    Returns:
        List of possible start times
        
    Example:
        Free: [(09:00, 12:00), (14:00, 16:00)]
        Duration: 50 minutes
        Step: 30 minutes
        Result: [09:00, 09:30, 10:00, 10:30, 11:00, 14:00, 14:30, 15:00]
    """
    if not free_intervals or duration_minutes <= 0:
        return []
    
    def time_to_minutes(t):
        return t.hour * 60 + t.minute
    
    def minutes_to_time(m):
        return dt_time(hour=m // 60, minute=m % 60)
    
    start_times = []
    
    for interval_start, interval_end in free_intervals:
        start_min = time_to_minutes(interval_start)
        end_min = time_to_minutes(interval_end)
        
        current = start_min
        
        # Enumerate start times with step_minutes increments
        while current + duration_minutes <= end_min:
            start_times.append(minutes_to_time(current))
            current += step_minutes
    
    return start_times


def get_available_start_times(coach, course, target_date: dt_date, step_minutes: int = 30) -> List[str]:
    """
    Get all available start times for a coach's course on a specific date.
    
    This is the main function that combines all the above helpers:
    1. Get coach's availability for the date
    2. Get all active bookings (pending/confirmed) for the coach on that date
    3. Calculate free intervals = availability - busy
    4. Enumerate possible start times
    
    Args:
        coach: CoachProfile instance
        course: Course instance
        target_date: date object for the target date
        step_minutes: Step size for enumerating start times (default: 30)
        
    Returns:
        List of start times in "HH:MM" format
    """
    from schedule.models import CoachAvailability
    from booking.models import Booking
    
    # Get coach's availability for the date
    availabilities = CoachAvailability.objects.filter(
        coach=coach,
        date=target_date
    ).values_list('start_time', 'end_time')
    
    if not availabilities:
        return []
    
    available_intervals = list(availabilities)
    
    # Get active bookings for the coach on this date
    start_of_day = datetime.combine(target_date, dt_time.min)
    end_of_day = datetime.combine(target_date, dt_time.max)
    
    active_bookings = Booking.objects.filter(
        coach=coach,
        status__in=['pending', 'confirmed'],
        start_datetime__lt=end_of_day,
        end_datetime__gt=start_of_day
    ).values_list('start_datetime', 'end_datetime')
    
    # Convert datetime to time for busy intervals
    busy_intervals = [
        (booking_start.time(), booking_end.time())
        for booking_start, booking_end in active_bookings
    ]
    
    # Calculate free intervals
    free_intervals = subtract_busy(available_intervals, busy_intervals)
    
    # Enumerate possible start times
    duration_minutes = course.duration
    start_times_obj = enumerate_starts(free_intervals, duration_minutes, step_minutes)
    
    # Convert to string format
    start_times_str = [t.strftime('%H:%M') for t in start_times_obj]
    
    return start_times_str
