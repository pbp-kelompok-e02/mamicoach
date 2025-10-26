"""
Comprehensive test cases for booking module including views and availability services
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, date, time, timedelta
from datetime import time as dt_time, date as dt_date
import json
import pytz

from booking.models import Booking
from booking.services.availability import (
    merge_intervals, 
    subtract_busy, 
    enumerate_starts,
    get_available_start_times
)
from courses_and_coach.models import Course, Category
from user_profile.models import CoachProfile, UserProfile
from schedule.models import ScheduleSlot, CoachAvailability


# ==================== Availability Service Tests ====================

class MergeIntervalsTest(TestCase):
    """Test cases for merge_intervals function"""
    
    def test_merge_empty_list(self):
        """Test merge with empty list"""
        result = merge_intervals([])
        self.assertEqual(result, [])
    
    def test_merge_single_interval(self):
        """Test merge with single interval"""
        intervals = [(dt_time(9, 0), dt_time(10, 0))]
        result = merge_intervals(intervals)
        self.assertEqual(result, intervals)
    
    def test_merge_non_overlapping_intervals(self):
        """Test merge with non-overlapping intervals"""
        intervals = [
            (dt_time(9, 0), dt_time(10, 0)),
            (dt_time(11, 0), dt_time(12, 0)),
            (dt_time(14, 0), dt_time(15, 0))
        ]
        result = merge_intervals(intervals)
        self.assertEqual(result, intervals)
    
    def test_merge_overlapping_intervals(self):
        """Test merge with overlapping intervals"""
        intervals = [
            (dt_time(9, 0), dt_time(11, 0)),
            (dt_time(10, 30), dt_time(12, 0))
        ]
        result = merge_intervals(intervals)
        expected = [(dt_time(9, 0), dt_time(12, 0))]
        self.assertEqual(result, expected)
    
    def test_merge_adjacent_intervals(self):
        """Test merge with adjacent intervals"""
        intervals = [
            (dt_time(9, 0), dt_time(10, 0)),
            (dt_time(10, 0), dt_time(11, 0))
        ]
        result = merge_intervals(intervals)
        expected = [(dt_time(9, 0), dt_time(11, 0))]
        self.assertEqual(result, expected)
    
    def test_merge_multiple_overlapping(self):
        """Test merge with multiple overlapping intervals"""
        intervals = [
            (dt_time(9, 0), dt_time(11, 0)),
            (dt_time(10, 30), dt_time(12, 0)),
            (dt_time(11, 30), dt_time(13, 0))
        ]
        result = merge_intervals(intervals)
        expected = [(dt_time(9, 0), dt_time(13, 0))]
        self.assertEqual(result, expected)
    
    def test_merge_unsorted_intervals(self):
        """Test merge with unsorted intervals"""
        intervals = [
            (dt_time(14, 0), dt_time(15, 0)),
            (dt_time(9, 0), dt_time(10, 0)),
            (dt_time(11, 0), dt_time(12, 0))
        ]
        result = merge_intervals(intervals)
        expected = [
            (dt_time(9, 0), dt_time(10, 0)),
            (dt_time(11, 0), dt_time(12, 0)),
            (dt_time(14, 0), dt_time(15, 0))
        ]
        self.assertEqual(result, expected)
    
    def test_merge_complex_overlapping(self):
        """Test merge with complex overlapping pattern"""
        intervals = [
            (dt_time(9, 0), dt_time(11, 0)),
            (dt_time(10, 0), dt_time(12, 0)),
            (dt_time(14, 0), dt_time(15, 0)),
            (dt_time(14, 30), dt_time(16, 0))
        ]
        result = merge_intervals(intervals)
        expected = [
            (dt_time(9, 0), dt_time(12, 0)),
            (dt_time(14, 0), dt_time(16, 0))
        ]
        self.assertEqual(result, expected)


class SubtractBusyTest(TestCase):
    """Test cases for subtract_busy function"""
    
    def test_subtract_empty_busy(self):
        """Test subtract with no busy intervals"""
        available = [(dt_time(9, 0), dt_time(17, 0))]
        busy = []
        result = subtract_busy(available, busy)
        self.assertEqual(result, available)
    
    def test_subtract_empty_available(self):
        """Test subtract with no available intervals"""
        available = []
        busy = [(dt_time(10, 0), dt_time(11, 0))]
        result = subtract_busy(available, busy)
        self.assertEqual(result, [])
    
    def test_subtract_single_busy_in_middle(self):
        """Test subtract single busy interval in middle"""
        available = [(dt_time(9, 0), dt_time(17, 0))]
        busy = [(dt_time(12, 0), dt_time(13, 0))]
        result = subtract_busy(available, busy)
        expected = [
            (dt_time(9, 0), dt_time(12, 0)),
            (dt_time(13, 0), dt_time(17, 0))
        ]
        self.assertEqual(result, expected)
    
    def test_subtract_multiple_busy(self):
        """Test subtract multiple busy intervals"""
        available = [(dt_time(9, 0), dt_time(15, 0))]
        busy = [
            (dt_time(10, 0), dt_time(11, 0)),
            (dt_time(13, 0), dt_time(14, 0))
        ]
        result = subtract_busy(available, busy)
        expected = [
            (dt_time(9, 0), dt_time(10, 0)),
            (dt_time(11, 0), dt_time(13, 0)),
            (dt_time(14, 0), dt_time(15, 0))
        ]
        self.assertEqual(result, expected)
    
    def test_subtract_busy_at_start(self):
        """Test subtract busy interval at start"""
        available = [(dt_time(9, 0), dt_time(17, 0))]
        busy = [(dt_time(9, 0), dt_time(10, 0))]
        result = subtract_busy(available, busy)
        expected = [(dt_time(10, 0), dt_time(17, 0))]
        self.assertEqual(result, expected)
    
    def test_subtract_busy_at_end(self):
        """Test subtract busy interval at end"""
        available = [(dt_time(9, 0), dt_time(17, 0))]
        busy = [(dt_time(16, 0), dt_time(17, 0))]
        result = subtract_busy(available, busy)
        expected = [(dt_time(9, 0), dt_time(16, 0))]
        self.assertEqual(result, expected)
    
    def test_subtract_multiple_available(self):
        """Test subtract with multiple available intervals"""
        available = [
            (dt_time(9, 0), dt_time(12, 0)),
            (dt_time(14, 0), dt_time(17, 0))
        ]
        busy = [
            (dt_time(10, 0), dt_time(11, 0)),
            (dt_time(15, 0), dt_time(16, 0))
        ]
        result = subtract_busy(available, busy)
        expected = [
            (dt_time(9, 0), dt_time(10, 0)),
            (dt_time(11, 0), dt_time(12, 0)),
            (dt_time(14, 0), dt_time(15, 0)),
            (dt_time(16, 0), dt_time(17, 0))
        ]
        self.assertEqual(result, expected)


class EnumerateStartsTest(TestCase):
    """Test cases for enumerate_starts function"""
    
    def test_enumerate_empty_intervals(self):
        """Test enumerate with empty intervals"""
        result = enumerate_starts([], 60)
        self.assertEqual(result, [])
    
    def test_enumerate_single_interval(self):
        """Test enumerate with single interval"""
        intervals = [(dt_time(9, 0), dt_time(12, 0))]
        result = enumerate_starts(intervals, 60)
        expected = [
            dt_time(9, 0),
            dt_time(9, 30),
            dt_time(10, 0),
            dt_time(10, 30),
            dt_time(11, 0)
        ]
        self.assertEqual(result, expected)
    
    def test_enumerate_exact_duration(self):
        """Test enumerate with interval exactly matching duration"""
        intervals = [(dt_time(9, 0), dt_time(10, 0))]
        result = enumerate_starts(intervals, 60)
        expected = [dt_time(9, 0)]
        self.assertEqual(result, expected)
    
    def test_enumerate_too_short_interval(self):
        """Test enumerate with interval shorter than duration"""
        intervals = [(dt_time(9, 0), dt_time(9, 30))]
        result = enumerate_starts(intervals, 60)
        self.assertEqual(result, [])
    
    def test_enumerate_different_step(self):
        """Test enumerate with different step size"""
        intervals = [(dt_time(9, 0), dt_time(10, 30))]
        result = enumerate_starts(intervals, 60, step_minutes=15)
        expected = [
            dt_time(9, 0),
            dt_time(9, 15),
            dt_time(9, 30)
        ]
        self.assertEqual(result, expected)
    
    def test_enumerate_multiple_intervals(self):
        """Test enumerate with multiple intervals"""
        intervals = [
            (dt_time(9, 0), dt_time(10, 0)),
            (dt_time(14, 0), dt_time(15, 0))
        ]
        result = enumerate_starts(intervals, 60)
        expected = [
            dt_time(9, 0),
            dt_time(14, 0)
        ]
        self.assertEqual(result, expected)
    
    def test_enumerate_90min_duration(self):
        """Test enumerate with 90-minute course"""
        intervals = [(dt_time(9, 0), dt_time(12, 0))]
        result = enumerate_starts(intervals, 90)
        expected = [
            dt_time(9, 0),
            dt_time(9, 30),
            dt_time(10, 0),
            dt_time(10, 30)
        ]
        self.assertEqual(result, expected)


class GetAvailableStartTimesTest(TestCase):
    """Test cases for get_available_start_times function"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create coach user
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.coach_user)
        
        # Create course
        self.category = Category.objects.create(name='Test')
        self.course = Course.objects.create(
            title='Test Course',
            coach=self.coach,
            price=100000,
            duration=60
        )
        
        # Create user for bookings
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user)
        
        # Test date
        self.test_date = dt_date.today() + timedelta(days=1)
    
    def test_no_availability(self):
        """Test with no availability set"""
        result = get_available_start_times(self.coach, self.course, self.test_date)
        self.assertEqual(result, [])
    
    def test_single_availability_slot(self):
        """Test with single availability slot"""
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=dt_time(9, 0),
            end_time=dt_time(12, 0)
        )
        
        result = get_available_start_times(self.coach, self.course, self.test_date)
        
        # Should have multiple start times within the availability
        self.assertGreater(len(result), 0)
        self.assertIn('09:00', result)
    
    def test_availability_with_booking(self):
        """Test availability with existing booking"""
        # Add availability
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=dt_time(9, 0),
            end_time=dt_time(17, 0)
        )
        
        # Add booking
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        start_dt = jakarta_tz.localize(datetime.combine(self.test_date, dt_time(10, 0)))
        end_dt = jakarta_tz.localize(datetime.combine(self.test_date, dt_time(11, 0)))
        
        Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=end_dt,
            status='confirmed'
        )
        
        result = get_available_start_times(self.coach, self.course, self.test_date)
        
        # Should exclude times during the booking
        self.assertNotIn('10:00', result)
        self.assertNotIn('10:30', result)
    
    def test_multiple_availability_slots(self):
        """Test with multiple availability slots"""
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=dt_time(9, 0),
            end_time=dt_time(12, 0)
        )
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=dt_time(14, 0),
            end_time=dt_time(17, 0)
        )
        
        result = get_available_start_times(self.coach, self.course, self.test_date)
        
        self.assertGreater(len(result), 0)
        self.assertIn('09:00', result)
        self.assertIn('14:00', result)
    
    def test_all_bookings_statuses(self):
        """Test that pending, paid, and confirmed bookings block time"""
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=dt_time(9, 0),
            end_time=dt_time(17, 0)
        )
        
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        
        # Test each booking status
        for status in ['pending', 'paid', 'confirmed']:
            # Clear previous bookings
            Booking.objects.all().delete()
            
            start_dt = jakarta_tz.localize(datetime.combine(self.test_date, dt_time(14, 0)))
            end_dt = jakarta_tz.localize(datetime.combine(self.test_date, dt_time(15, 0)))
            
            Booking.objects.create(
                user=self.user,
                coach=self.coach,
                course=self.course,
                start_datetime=start_dt,
                end_datetime=end_dt,
                status=status
            )
            
            result = get_available_start_times(self.coach, self.course, self.test_date)
            
            # 14:00 should not be available for any of these statuses
            self.assertNotIn('14:00', result, f"Status '{status}' should block 14:00")
    
    def test_done_booking_does_not_block(self):
        """Test that completed bookings don't block availability"""
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=dt_time(9, 0),
            end_time=dt_time(17, 0)
        )
        
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        start_dt = jakarta_tz.localize(datetime.combine(self.test_date, dt_time(14, 0)))
        end_dt = jakarta_tz.localize(datetime.combine(self.test_date, dt_time(15, 0)))
        
        Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=end_dt,
            status='done'
        )
        
        result = get_available_start_times(self.coach, self.course, self.test_date)
        
        # Done bookings should not block time
        self.assertIn('14:00', result)
    
    def test_time_format_hhmm(self):
        """Test that returned times are in HH:MM format"""
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=dt_time(9, 0),
            end_time=dt_time(10, 0)
        )
        
        result = get_available_start_times(self.coach, self.course, self.test_date)
        
        for time_str in result:
            # Should match HH:MM format
            self.assertRegex(time_str, r'^\d{2}:\d{2}$')
    
    def test_custom_step_size(self):
        """Test with custom step size"""
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=dt_time(9, 0),
            end_time=dt_time(10, 0)
        )
        
        result = get_available_start_times(self.coach, self.course, self.test_date, step_minutes=15)
        
        # With 15-minute steps for a 60-minute course in 1 hour window
        # Should have: 09:00 (can fit 60min ending at 10:00)
        # 09:15 won't work (would end at 10:15, outside window)
        self.assertEqual(len(result), 1)


# ==================== Booking Views Tests ====================

class GetAvailableDatesViewTest(TestCase):
    """Test cases for get_available_dates view"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create coach
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.coach_user)
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user)
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_get_available_dates_requires_login(self):
        """Test endpoint requires authentication"""
        self.client.logout()
        response = self.client.get(
            f'/booking/get_available_dates/{self.coach.id}/?year=2025&month=10'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_get_available_dates_invalid_coach(self):
        """Test with invalid coach ID"""
        response = self.client.get('/booking/get_available_dates/99999/?year=2025&month=10')
        self.assertEqual(response.status_code, 404)
    
    def test_get_available_dates_valid_request(self):
        """Test valid request"""
        response = self.client.get(
            f'/booking/get_available_dates/{self.coach.id}/?year=2025&month=10'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('available_dates', data)
        self.assertIn('year', data)
        self.assertIn('month', data)
        self.assertIn('month_name', data)
    
    def test_get_available_dates_default_month(self):
        """Test with default month (current)"""
        response = self.client.get(f'/booking/get_available_dates/{self.coach.id}/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIsNotNone(data['month'])
    
    def test_get_available_dates_with_schedule_slots(self):
        """Test dates with schedule slots"""
        future_date = date.today() + timedelta(days=5)
        ScheduleSlot.objects.create(
            coach=self.coach,
            date=future_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_available=True
        )
        
        response = self.client.get(
            f'/booking/get_available_dates/{self.coach.id}/?year={future_date.year}&month={future_date.month}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertGreater(len(data['available_dates']), 0)


class GetAvailableTimesViewTest(TestCase):
    """Test cases for get_available_times view"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create coach
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.coach_user)
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user)
        
        self.client.login(username='testuser', password='testpass123')
        self.test_date = date.today() + timedelta(days=1)
    
    def test_get_available_times_requires_login(self):
        """Test endpoint requires authentication"""
        self.client.logout()
        response = self.client.get(
            f'/booking/get_available_times/{self.coach.id}/?date={self.test_date}'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_get_available_times_missing_date(self):
        """Test missing date parameter"""
        response = self.client.get(
            f'/booking/get_available_times/{self.coach.id}/'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_get_available_times_invalid_date_format(self):
        """Test invalid date format"""
        response = self.client.get(
            f'/booking/get_available_times/{self.coach.id}/?date=invalid'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_get_available_times_valid_request(self):
        """Test valid request"""
        response = self.client.get(
            f'/booking/get_available_times/{self.coach.id}/?date={self.test_date.isoformat()}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('available_times', data)
        self.assertIn('date', data)
        self.assertIn('day_name', data)
    
    def test_get_available_times_with_slots(self):
        """Test times with available slots"""
        ScheduleSlot.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_available=True
        )
        
        response = self.client.get(
            f'/booking/get_available_times/{self.coach.id}/?date={self.test_date.isoformat()}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertGreater(len(data['available_times']), 0)


class CreateBookingViewTest(TestCase):
    """Test cases for create_booking view"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create coach
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.coach_user)
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user)
        
        # Create category and course
        self.category = Category.objects.create(name='Test')
        self.course = Course.objects.create(
            title='Test Course',
            coach=self.coach,
            price=100000,
            duration=60
        )
        
        # Create schedule slot
        self.test_date = date.today() + timedelta(days=1)
        self.schedule = ScheduleSlot.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=time(9, 0),
            end_time=time(10, 0),
            is_available=True
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_create_booking_requires_login(self):
        """Test endpoint requires authentication"""
        self.client.logout()
        response = self.client.post(
            f'/booking/create_booking/{self.course.id}/',
            data=json.dumps({
                'schedule_id': self.schedule.id,
                'date': self.test_date.isoformat()
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_create_booking_requires_post(self):
        """Test endpoint requires POST method"""
        response = self.client.get(
            f'/booking/create_booking/{self.course.id}/'
        )
        self.assertEqual(response.status_code, 405)
    
    def test_create_booking_missing_schedule(self):
        """Test with missing schedule_id"""
        response = self.client.post(
            f'/booking/create_booking/{self.course.id}/',
            data=json.dumps({
                'date': self.test_date.isoformat()
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_create_booking_missing_date(self):
        """Test with missing date"""
        response = self.client.post(
            f'/booking/create_booking/{self.course.id}/',
            data=json.dumps({
                'schedule_id': self.schedule.id
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_create_booking_invalid_schedule(self):
        """Test with schedule from different coach"""
        other_coach_user = User.objects.create_user(
            username='othercoach',
            password='testpass123'
        )
        other_coach = CoachProfile.objects.create(user=other_coach_user)
        other_schedule = ScheduleSlot.objects.create(
            coach=other_coach,
            date=self.test_date,
            start_time=time(9, 0),
            end_time=time(10, 0)
        )
        
        response = self.client.post(
            f'/booking/create_booking/{self.course.id}/',
            data=json.dumps({
                'schedule_id': other_schedule.id,
                'date': self.test_date.isoformat()
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_create_booking_date_mismatch(self):
        """Test with date not matching schedule"""
        wrong_date = date.today() + timedelta(days=5)
        response = self.client.post(
            f'/booking/create_booking/{self.course.id}/',
            data=json.dumps({
                'schedule_id': self.schedule.id,
                'date': wrong_date.isoformat()
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_create_booking_success(self):
        """Test successful booking creation"""
        response = self.client.post(
            f'/booking/create_booking/{self.course.id}/',
            data=json.dumps({
                'schedule_id': self.schedule.id,
                'date': self.test_date.isoformat()
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('booking_id', data)


class ApiCourseStartTimesViewTest(TestCase):
    """Test cases for api_course_start_times view"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create coach
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.coach_user)
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user)
        
        # Create course
        self.category = Category.objects.create(name='Test')
        self.course = Course.objects.create(
            title='Test Course',
            coach=self.coach,
            price=100000,
            duration=60
        )
        
        self.test_date = date.today() + timedelta(days=1)
        self.client.login(username='testuser', password='testpass123')
    
    def test_api_start_times_requires_login(self):
        """Test endpoint requires authentication"""
        self.client.logout()
        response = self.client.get(
            f'/booking/api/course/{self.course.id}/start-times/?date={self.test_date}'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_api_start_times_missing_date(self):
        """Test missing date parameter"""
        response = self.client.get(
            f'/booking/api/course/{self.course.id}/start-times/'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_api_start_times_invalid_date_format(self):
        """Test invalid date format"""
        response = self.client.get(
            f'/booking/api/course/{self.course.id}/start-times/?date=invalid'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_api_start_times_valid_request(self):
        """Test valid request"""
        # Add availability for the coach
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        
        response = self.client.get(
            f'/booking/api/course/{self.course.id}/start-times/?date={self.test_date.isoformat()}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('date', data)
        self.assertIn('start_times', data)
        self.assertIn('course_duration', data)
        self.assertIn('course_title', data)
    
    def test_api_start_times_no_availability(self):
        """Test with no availability"""
        response = self.client.get(
            f'/booking/api/course/{self.course.id}/start-times/?date={self.test_date.isoformat()}'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['start_times']), 0)


class ApiBookingCreateViewTest(TestCase):
    """Test cases for api_booking_create view"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create coach
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.coach_user)
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user)
        
        # Create course
        self.category = Category.objects.create(name='Test')
        self.course = Course.objects.create(
            title='Test Course',
            coach=self.coach,
            price=100000,
            duration=60
        )
        
        # Add availability
        self.test_date = date.today() + timedelta(days=1)
        CoachAvailability.objects.create(
            coach=self.coach,
            date=self.test_date,
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_api_booking_create_requires_login(self):
        """Test endpoint requires authentication"""
        self.client.logout()
        response = self.client.post(
            f'/booking/api/booking-create/{self.course.id}/',
            data=json.dumps({
                'date': self.test_date.isoformat(),
                'start_time': '09:00'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_api_booking_create_missing_date(self):
        """Test missing date parameter"""
        response = self.client.post(
            f'/booking/api/booking-create/{self.course.id}/',
            data=json.dumps({
                'start_time': '09:00'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_api_booking_create_missing_start_time(self):
        """Test missing start_time parameter"""
        response = self.client.post(
            f'/booking/api/booking-create/{self.course.id}/',
            data=json.dumps({
                'date': self.test_date.isoformat()
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_api_booking_create_success(self):
        """Test successful booking creation"""
        response = self.client.post(
            f'/booking/api/booking-create/{self.course.id}/',
            data=json.dumps({
                'date': self.test_date.isoformat(),
                'start_time': '09:00'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify booking was created
        booking = Booking.objects.get(user=self.user, course=self.course)
        self.assertEqual(booking.status, 'pending')
    
    def test_api_booking_create_overlap_detection(self):
        """Test that overlapping bookings are detected"""
        # Create first booking
        jakarta_tz = pytz.timezone('Asia/Jakarta')
        start_dt = jakarta_tz.localize(datetime.combine(self.test_date, time(9, 0)))
        end_dt = start_dt + timedelta(minutes=60)
        
        Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=end_dt,
            status='confirmed'
        )
        
        # Try to create overlapping booking
        response = self.client.post(
            f'/booking/api/booking-create/{self.course.id}/',
            data=json.dumps({
                'date': self.test_date.isoformat(),
                'start_time': '09:00'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
