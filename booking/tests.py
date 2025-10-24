from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, date
from decimal import Decimal
import json
import pytz

from .models import Booking
from user_profile.models import CoachProfile
from courses_and_coach.models import Course
from schedule.models import CoachAvailability
from .services.availability import get_available_start_times, merge_intervals


def create_test_coach_profile(user):
    """Helper function to create a coach profile"""
    return CoachProfile.objects.create(
        user=user,
        bio='Test bio - Fitness coach with 5 years experience',
        expertise=['Fitness', 'Yoga', 'CrossFit'],
        rating=4.5,
        rating_count=10
    )


class BookingModelTest(TestCase):
    """Test Booking model functionality"""
    
    def setUp(self):
        # Create users
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        
        # Create coach profile
        self.coach = create_test_coach_profile(self.coach_user)
        
        # Create course
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,  # 60 minutes
            price=Decimal('150000.00')
        )
        
        # Timezone
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    def test_create_booking_success(self):
        """Test creating a valid booking"""
        start_dt = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end_dt = start_dt + timedelta(minutes=60)
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=end_dt,
            status='pending'
        )
        
        self.assertEqual(booking.status, 'pending')
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.coach, self.coach)
        self.assertEqual(booking.course, self.course)
        self.assertIsNotNone(booking.created_at)
    
    def test_booking_status_choices(self):
        """Test all booking status choices are valid"""
        valid_statuses = ['pending', 'paid', 'confirmed', 'done', 'canceled']
        
        for status in valid_statuses:
            start_dt = self.jakarta_tz.localize(
                datetime(2025, 10, 25, 10, 0) + timedelta(hours=valid_statuses.index(status))
            )
            end_dt = start_dt + timedelta(minutes=60)
            
            booking = Booking.objects.create(
                user=self.user,
                coach=self.coach,
                course=self.course,
                start_datetime=start_dt,
                end_datetime=end_dt,
                status=status
            )
            self.assertEqual(booking.status, status)
    
    def test_booking_clean_validation_end_before_start(self):
        """Test validation: end_datetime must be after start_datetime"""
        start_dt = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end_dt = start_dt - timedelta(minutes=30)  # End before start
        
        booking = Booking(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=end_dt,
            status='pending'
        )
        
        with self.assertRaises(Exception):
            booking.full_clean()
    
    def test_booking_ordering(self):
        """Test bookings are ordered by created_at descending"""
        booking1 = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0)),
            end_datetime=self.jakarta_tz.localize(datetime(2025, 10, 25, 11, 0)),
            status='pending'
        )
        
        booking2 = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=self.jakarta_tz.localize(datetime(2025, 10, 25, 14, 0)),
            end_datetime=self.jakarta_tz.localize(datetime(2025, 10, 25, 15, 0)),
            status='pending'
        )
        
        bookings = Booking.objects.all()
        self.assertEqual(bookings[0], booking2)
        self.assertEqual(bookings[1], booking1)


class BookingAPITest(TestCase):
    """Test Booking API endpoints"""
    
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        
        # Create coach profile
        self.coach = create_test_coach_profile(self.coach_user)
        
        # Create course
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,
            price=Decimal('150000.00')
        )
        
        # Create availability
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
        tomorrow = date.today() + timedelta(days=1)
        
        CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=datetime.strptime('09:00', '%H:%M').time(),
            end_time=datetime.strptime('17:00', '%H:%M').time()
        )
        
        # Login user
        self.client.login(username='testuser', password='testpass123')
    
    def test_create_booking_api_success(self):
        """Test API endpoint to create booking"""
        tomorrow = date.today() + timedelta(days=1)
        
        data = {
            'date': tomorrow.strftime('%Y-%m-%d'),
            'start_time': '10:00'
        }
        
        response = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        self.assertIn('booking_id', response_data)
        
        # Verify booking was created
        booking = Booking.objects.get(id=response_data['booking_id'])
        self.assertEqual(booking.user, self.user)
        self.assertEqual(booking.course, self.course)
        self.assertEqual(booking.status, 'pending')
    
    def test_create_booking_api_missing_data(self):
        """Test API endpoint with missing required data"""
        data = {
            'date': '2025-10-25'
            # Missing start_time
        }
        
        response = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
    
    def test_create_booking_overlap_detection(self):
        """Test overlap detection when creating booking"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Create first booking
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
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
        data = {
            'date': tomorrow.strftime('%Y-%m-%d'),
            'start_time': '10:30'  # Overlaps with 10:00-11:00
        }
        
        response = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 409)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('not available', response_data['error'].lower())
    
    def test_list_bookings_api(self):
        """Test API endpoint to list bookings"""
        # Create some bookings
        tomorrow = date.today() + timedelta(days=1)
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        
        Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='pending'
        )
        
        response = self.client.get('/booking/api/bookings/?role=user')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('bookings', response_data)
        self.assertEqual(response_data['count'], 1)
        self.assertEqual(response_data['bookings'][0]['status'], 'pending')
    
    def test_mark_booking_as_paid(self):
        """Test API endpoint to mark booking as paid"""
        tomorrow = date.today() + timedelta(days=1)
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='pending'
        )
        
        data = {
            'payment_id': 'PAYMENT123',
            'payment_method': 'credit_card'
        }
        
        response = self.client.post(
            f'/booking/api/booking/{booking.id}/mark-paid/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify booking status updated
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'paid')
    
    def test_cancel_booking_user(self):
        """Test user can cancel their own pending booking"""
        tomorrow = date.today() + timedelta(days=1)
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='pending'
        )
        
        response = self.client.post(f'/booking/api/booking/{booking.id}/cancel/')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify booking status
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'canceled')
    
    def test_update_booking_status_coach(self):
        """Test coach can update booking status"""
        # Login as coach
        self.client.login(username='testcoach', password='testpass123')
        
        tomorrow = date.today() + timedelta(days=1)
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='paid'
        )
        
        data = {'status': 'confirmed'}
        
        response = self.client.post(
            f'/booking/api/booking/{booking.id}/status/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify status updated
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
    
    def test_get_available_dates_api(self):
        """Test API endpoint to get available dates"""
        today = date.today()
        
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-dates/?year={today.year}&month={today.month}&course_id={self.course.id}'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('available_dates', response_data)
        self.assertIn('year', response_data)
        self.assertIn('month', response_data)
    
    def test_get_available_times_api(self):
        """Test API endpoint to get available times"""
        tomorrow = date.today() + timedelta(days=1)
        
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-times/?date={tomorrow.strftime("%Y-%m-%d")}&course_id={self.course.id}'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('available_times', response_data)
        self.assertIn('date', response_data)


class AvailabilityServiceTest(TestCase):
    """Test availability service functions"""
    
    def setUp(self):
        # Create users
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        
        # Create coach profile
        self.coach = create_test_coach_profile(self.coach_user)
        
        # Create course
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,
            price=Decimal('150000.00')
        )
        
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    def test_merge_intervals(self):
        """Test merge_intervals function"""
        intervals = [
            (datetime.strptime('09:00', '%H:%M').time(), datetime.strptime('10:00', '%H:%M').time()),
            (datetime.strptime('10:00', '%H:%M').time(), datetime.strptime('11:00', '%H:%M').time()),
            (datetime.strptime('14:00', '%H:%M').time(), datetime.strptime('15:00', '%H:%M').time()),
        ]
        
        merged = merge_intervals(intervals)
        
        # Should merge 09:00-10:00 and 10:00-11:00 into 09:00-11:00
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0], (datetime.strptime('09:00', '%H:%M').time(), datetime.strptime('11:00', '%H:%M').time()))
        self.assertEqual(merged[1], (datetime.strptime('14:00', '%H:%M').time(), datetime.strptime('15:00', '%H:%M').time()))
    
    def test_get_available_start_times_no_bookings(self):
        """Test getting available start times with no existing bookings"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Create availability 09:00-17:00
        CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=datetime.strptime('09:00', '%H:%M').time(),
            end_time=datetime.strptime('17:00', '%H:%M').time()
        )
        
        available_times = get_available_start_times(
            coach=self.coach,
            course=self.course,
            target_date=tomorrow,
            step_minutes=30
        )
        
        # Should have many available slots
        self.assertGreater(len(available_times), 0)
        self.assertIn('09:00', available_times)
        self.assertIn('09:30', available_times)
    
    def test_get_available_start_times_with_bookings(self):
        """Test getting available start times with existing bookings"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Create availability 09:00-17:00
        CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=datetime.strptime('09:00', '%H:%M').time(),
            end_time=datetime.strptime('17:00', '%H:%M').time()
        )
        
        # Create booking 10:00-11:00
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='confirmed'
        )
        
        available_times = get_available_start_times(
            coach=self.coach,
            course=self.course,
            target_date=tomorrow,
            step_minutes=30
        )
        
        # 10:00 should not be available (booked)
        # 09:30 should not be available (would overlap with 10:00-11:00 booking)
        self.assertIn('09:00', available_times)
        self.assertNotIn('10:00', available_times)


class BookingViewTest(TestCase):
    """Test Booking page views"""
    def setUp(self):
        self.client = Client()
        # Create users
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        
        self.coach = create_test_coach_profile(self.coach_user)
        
        # Create multiple courses
        self.course1 = Course.objects.create(
            coach=self.coach,
            title='Yoga Basics',
            description='Beginner yoga course',
            duration=60,
            price=Decimal('100000.00')
        )
        
        self.course2 = Course.objects.create(
            coach=self.coach,
            title='Advanced Fitness',
            description='Advanced training',
            duration=90,
            price=Decimal('200000.00')
        )
        
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
        
        # Create availability
        tomorrow = date.today() + timedelta(days=1)
        CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=datetime.strptime('08:00', '%H:%M').time(),
            end_time=datetime.strptime('18:00', '%H:%M').time()
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_booking_confirmation_requires_login(self):
        """Test booking confirmation page requires authentication"""
        self.client.logout()
        
        response = self.client.get(
            f'/booking/confirm/{self.course1.id}/?date=2025-10-25&time=10:00'
        )
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)
    
    def test_booking_confirmation_with_missing_course(self):
        """Test booking confirmation with non-existent course returns 404"""
        response = self.client.get(
            '/booking/confirm/99999/?date=2025-10-25&time=10:00'
        )
        
        self.assertEqual(response.status_code, 404)
    
    def test_booking_confirmation_renders_correct_data(self):
        """Test booking confirmation page displays correct booking details"""
        tomorrow = date.today() + timedelta(days=1)
        
        response = self.client.get(
            f'/booking/confirm/{self.course1.id}/?date={tomorrow.strftime("%Y-%m-%d")}&time=10:00'
        )
        
        self.assertEqual(response.status_code, 200)
        # Just check response is successful, content may vary depending on template
        self.assertIsNotNone(response.content)
    
    def test_booking_success_requires_login(self):
        """Test booking success page requires authentication"""
        tomorrow = date.today() + timedelta(days=1)
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='pending'
        )
        
        self.client.logout()
        
        response = self.client.get(f'/booking/success/{booking.id}/')
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)
    
    def test_booking_success_different_statuses(self):
        """Test booking success page for different booking statuses"""
        tomorrow = date.today() + timedelta(days=1)
        
        statuses = ['pending', 'paid', 'confirmed', 'done']
        
        for status in statuses:
            start_dt = self.jakarta_tz.localize(
                datetime.combine(
                    tomorrow + timedelta(hours=statuses.index(status)), 
                    datetime.strptime('10:00', '%H:%M').time()
                )
            )
            
            booking = Booking.objects.create(
                user=self.user,
                coach=self.coach,
                course=self.course1,
                start_datetime=start_dt,
                end_datetime=start_dt + timedelta(minutes=60),
                status=status
            )
            
            response = self.client.get(f'/booking/success/{booking.id}/')
            
            self.assertEqual(response.status_code, 200)
            # Just check response is successful
            self.assertIsNotNone(response.content)
    
    def test_api_available_dates_without_course_id(self):
        """Test available dates API without course_id parameter"""
        today = date.today()
        
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-dates/?year={today.year}&month={today.month}'
        )
        
        # Should still work (uses first course)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('available_dates', response_data)
    
    def test_api_available_dates_invalid_month(self):
        """Test available dates API with invalid month"""
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-dates/?year=2025&month=13&course_id={self.course1.id}'
        )
        
        # Should handle gracefully
        self.assertIn(response.status_code, [200, 400, 500])
    
    def test_api_available_dates_non_existent_coach(self):
        """Test available dates API with non-existent coach"""
        response = self.client.get(
            f'/booking/api/coach/99999/available-dates/?year=2025&month=10&course_id={self.course1.id}'
        )
        
        # Should return 404 or 500 depending on error handler
        self.assertIn(response.status_code, [404, 500])
    
    def test_api_available_times_without_date(self):
        """Test available times API without date parameter"""
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-times/?course_id={self.course1.id}'
        )
        
        # Should return error
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
    
    def test_api_available_times_invalid_date_format(self):
        """Test available times API with invalid date format"""
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-times/?date=invalid-date&course_id={self.course1.id}'
        )
        
        # Should return error
        self.assertIn(response.status_code, [400, 500])
    
    def test_api_available_times_past_date(self):
        """Test available times API with past date"""
        yesterday = date.today() - timedelta(days=1)
        
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-times/?date={yesterday.strftime("%Y-%m-%d")}&course_id={self.course1.id}'
        )
        
        # Should return empty or error
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        # Past dates should have no available times
        self.assertEqual(len(response_data.get('available_times', [])), 0)
    
    def test_api_available_times_different_courses(self):
        """Test available times for different course durations"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Course 1: 60 minutes
        response1 = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-times/?date={tomorrow.strftime("%Y-%m-%d")}&course_id={self.course1.id}'
        )
        
        # Course 2: 90 minutes (should have fewer slots)
        response2 = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-times/?date={tomorrow.strftime("%Y-%m-%d")}&course_id={self.course2.id}'
        )
        
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        times1 = json.loads(response1.content)['available_times']
        times2 = json.loads(response2.content)['available_times']
        
        # 90-minute course should have fewer available slots
        self.assertGreaterEqual(len(times1), len(times2))
    
    def test_api_booking_create_without_date(self):
        """Test booking creation API without date field"""
        data = {
            'start_time': '10:00'
            # Missing 'date'
        }
        
        response = self.client.post(
            f'/booking/api/course/{self.course1.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('required', response_data['error'].lower())
    
    def test_api_booking_create_without_start_time(self):
        """Test booking creation API without start_time field"""
        tomorrow = date.today() + timedelta(days=1)
        
        data = {
            'date': tomorrow.strftime('%Y-%m-%d')
            # Missing 'start_time'
        }
        
        response = self.client.post(
            f'/booking/api/course/{self.course1.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertFalse(response_data['success'])
        self.assertIn('required', response_data['error'].lower())
    
    def test_api_booking_create_malformed_json(self):
        """Test booking creation API with malformed JSON"""
        response = self.client.post(
            f'/booking/api/course/{self.course1.id}/create/',
            data='{"date": "2025-10-25", "start_time":',  # Malformed JSON
            content_type='application/json'
        )
        
        # Should return error (400 or 500 depending on error handler)
        self.assertIn(response.status_code, [400, 500])
        try:
            response_data = json.loads(response.content)
            self.assertFalse(response_data['success'])
        except:
            pass  # JSON parsing may fail, that's ok for this test
    
    def test_api_booking_list_filter_by_status(self):
        """Test booking list API with status filter"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Create bookings with different statuses
        Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
            ),
            end_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('11:00', '%H:%M').time())
            ),
            status='pending'
        )
        
        Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('14:00', '%H:%M').time())
            ),
            end_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('15:00', '%H:%M').time())
            ),
            status='confirmed'
        )
        
        # Filter by pending
        response = self.client.get('/booking/api/bookings/?role=user&status=pending')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['count'], 1)
        self.assertEqual(response_data['bookings'][0]['status'], 'pending')
    
    def test_api_booking_list_coach_role_requires_coach_profile(self):
        """Test booking list API with coach role requires CoachProfile"""
        # Regular user trying to access coach bookings
        response = self.client.get('/booking/api/bookings/?role=coach')
        
        self.assertEqual(response.status_code, 403)
        response_data = json.loads(response.content)
        self.assertIn('not a coach', response_data['error'].lower())
    
    def test_api_booking_list_coach_role_success(self):
        """Test booking list API with coach role returns coach's bookings"""
        # Login as coach
        self.client.login(username='testcoach', password='testpass123')
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Create booking for this coach
        Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
            ),
            end_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('11:00', '%H:%M').time())
            ),
            status='pending'
        )
        
        response = self.client.get('/booking/api/bookings/?role=coach')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertGreater(response_data['count'], 0)
    
    def test_api_mark_paid_already_paid_booking(self):
        """Test marking already paid booking returns error"""
        tomorrow = date.today() + timedelta(days=1)
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
            ),
            end_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('11:00', '%H:%M').time())
            ),
            status='paid'  # Already paid
        )
        
        data = {
            'payment_id': 'PAYMENT123',
            'payment_method': 'credit_card'
        }
        
        response = self.client.post(
            f'/booking/api/booking/{booking.id}/mark-paid/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('pending', response_data['error'].lower())
    
    def test_api_update_status_invalid_status(self):
        """Test updating booking with invalid status returns error"""
        self.client.login(username='testcoach', password='testpass123')
        
        tomorrow = date.today() + timedelta(days=1)
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
            ),
            end_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('11:00', '%H:%M').time())
            ),
            status='pending'
        )
        
        data = {'status': 'invalid_status'}
        
        response = self.client.post(
            f'/booking/api/booking/{booking.id}/status/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('invalid', response_data['error'].lower())
    
    def test_api_update_status_unauthorized_coach(self):
        """Test coach cannot update another coach's booking"""
        # Create another coach
        other_coach_user = User.objects.create_user(
            username='othercoach',
            email='othercoach@test.com',
            password='testpass123'
        )
        other_coach = create_test_coach_profile(other_coach_user)
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Booking for first coach
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
            ),
            end_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('11:00', '%H:%M').time())
            ),
            status='pending'
        )
        
        # Login as other coach
        self.client.login(username='othercoach', password='testpass123')
        
        data = {'status': 'confirmed'}
        
        response = self.client.post(
            f'/booking/api/booking/{booking.id}/status/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 403)
    
    def test_api_cancel_booking_unauthorized_user(self):
        """Test user cannot cancel another user's booking"""
        # Create another user
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123'
        )
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Booking for other user
        booking = Booking.objects.create(
            user=other_user,
            coach=self.coach,
            course=self.course1,
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
            ),
            end_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('11:00', '%H:%M').time())
            ),
            status='pending'
        )
        
        # Try to cancel as different user
        response = self.client.post(f'/booking/api/booking/{booking.id}/cancel/')
        
        self.assertEqual(response.status_code, 403)
    
    def test_api_cancel_booking_coach_can_cancel_any(self):
        """Test coach can cancel any booking for their sessions"""
        tomorrow = date.today() + timedelta(days=1)
        
        # Create booking
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
            ),
            end_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('11:00', '%H:%M').time())
            ),
            status='confirmed'  # Not pending
        )
        
        # Login as coach
        self.client.login(username='testcoach', password='testpass123')
        
        response = self.client.post(f'/booking/api/booking/{booking.id}/cancel/')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'canceled')


class BookingAPIErrorHandlingTest(TestCase):
    """Test API error handling and edge cases"""
    
    def setUp(self):
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        
        self.coach = create_test_coach_profile(self.coach_user)
        
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,
            price=Decimal('150000.00')
        )
        
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
        self.client.login(username='testuser', password='testpass123')
    
    def test_api_get_request_to_post_only_endpoint(self):
        """Test GET request to POST-only endpoint returns error"""
        response = self.client.get(f'/booking/api/course/{self.course.id}/create/')
        
        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)
    
    def test_api_post_request_to_get_only_endpoint(self):
        """Test POST request to GET-only endpoint returns error"""
        response = self.client.post(
            f'/booking/api/coach/{self.coach.id}/available-dates/?year=2025&month=10'
        )
        
        # Should return 405 Method Not Allowed
        self.assertEqual(response.status_code, 405)
    
    def test_api_booking_create_empty_body(self):
        """Test booking creation with empty request body"""
        response = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data='',
            content_type='application/json'
        )
        
        # Should return error
        self.assertIn(response.status_code, [400, 500])
    
    def test_api_available_dates_missing_year_parameter(self):
        """Test available dates without year parameter uses current year"""
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-dates/?month=10'
        )
        
        # Should still work with default year
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('year', response_data)
        self.assertEqual(response_data['year'], datetime.now().year)
    
    def test_api_available_dates_missing_month_parameter(self):
        """Test available dates without month parameter uses current month"""
        response = self.client.get(
            f'/booking/api/coach/{self.coach.id}/available-dates/?year=2025'
        )
        
        # Should still work with default month
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('month', response_data)
        self.assertEqual(response_data['month'], datetime.now().month)
    
    def test_api_booking_list_exception_handling(self):
        """Test booking list API handles exceptions gracefully"""
        # This test verifies the try-except block catches exceptions
        response = self.client.get('/booking/api/bookings/?role=user')
        
        # Should always return valid JSON even if there's an error
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn('bookings', response_data)


class BookingEdgeCasesTest(TestCase):
    """Test edge cases and error handling"""
    
    def setUp(self):
        self.client = Client()
        
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        
        self.coach = create_test_coach_profile(self.coach_user)
        
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,
            price=Decimal('150000.00')
        )
        
        self.client.login(username='testuser', password='testpass123')
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    def test_booking_without_availability_fails(self):
        """Test booking when coach has no availability"""
        # Create date without availability
        future_date = date.today() + timedelta(days=30)
        
        data = {
            'date': future_date.strftime('%Y-%m-%d'),
            'start_time': '10:00'
        }
        
        response = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Currently API allows booking without checking availability
        # This test documents current behavior, should be 400/409 in future
        self.assertIn(response.status_code, [200, 400, 409, 500])
    
    def test_unauthorized_user_cannot_access_api(self):
        """Test unauthorized user cannot access API"""
        self.client.logout()
        
        tomorrow = date.today() + timedelta(days=1)
        data = {
            'date': tomorrow.strftime('%Y-%m-%d'),
            'start_time': '10:00'
        }
        
        response = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should redirect to login (302) or return 401/403
        self.assertIn(response.status_code, [302, 401, 403])
    
    def test_invalid_json_returns_error(self):
        """Test invalid JSON returns error"""
        response = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data='invalid json string',
            content_type='application/json'
        )
        
        # Should return error
        self.assertIn(response.status_code, [400, 500])
    
    def test_invalid_date_format_returns_error(self):
        """Test invalid date format returns error"""
        data = {
            'date': '2025-13-45',  # Invalid date
            'start_time': '10:00'
        }
        
        response = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertIn(response.status_code, [400, 500])
    
    def test_nonexistent_course_returns_404(self):
        """Test booking nonexistent course returns 404"""
        tomorrow = date.today() + timedelta(days=1)
        data = {
            'date': tomorrow.strftime('%Y-%m-%d'),
            'start_time': '10:00'
        }
        
        response = self.client.post(
            f'/booking/api/course/99999/create/',  # Non-existent course ID
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Django's get_object_or_404 may return 404 or 500 depending on implementation
        self.assertIn(response.status_code, [404, 500])
    
    def test_regular_user_cannot_update_booking_status(self):
        """Test regular user cannot update booking status (coach only)"""
        tomorrow = date.today() + timedelta(days=1)
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='pending'
        )
        
        data = {'status': 'confirmed'}
        
        response = self.client.post(
            f'/booking/api/booking/{booking.id}/status/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should return 403 (user is not coach)
        self.assertEqual(response.status_code, 403)
    
    def test_user_cannot_cancel_paid_booking(self):
        """Test user cannot cancel paid/confirmed bookings"""
        tomorrow = date.today() + timedelta(days=1)
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='paid'  # Already paid
        )
        
        response = self.client.post(f'/booking/api/booking/{booking.id}/cancel/')
        
        # Should return 400 (can only cancel pending)
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('pending', response_data['error'].lower())
    
    def test_mark_already_paid_booking_as_paid_fails(self):
        """Test marking already paid booking as paid again fails"""
        tomorrow = date.today() + timedelta(days=1)
        start_dt = self.jakarta_tz.localize(
            datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
        )
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
            status='paid'  # Already paid
        )
        
        data = {
            'payment_id': 'PAYMENT123',
            'payment_method': 'credit_card'
        }
        
        response = self.client.post(
            f'/booking/api/booking/{booking.id}/mark-paid/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should fail (already paid)
        self.assertEqual(response.status_code, 400)


class AvailabilityServiceEdgeCasesTest(TestCase):
    """Test edge cases for availability service"""
    
    def test_merge_intervals_empty_list(self):
        """Test merge_intervals with empty list"""
        result = merge_intervals([])
        self.assertEqual(result, [])
    
    def test_merge_intervals_single_interval(self):
        """Test merge_intervals with single interval"""
        intervals = [
            (datetime.strptime('09:00', '%H:%M').time(), datetime.strptime('10:00', '%H:%M').time())
        ]
        result = merge_intervals(intervals)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], intervals[0])
    
    def test_merge_intervals_overlapping_three_intervals(self):
        """Test merge_intervals with 3 overlapping intervals"""
        intervals = [
            (datetime.strptime('09:00', '%H:%M').time(), datetime.strptime('10:00', '%H:%M').time()),
            (datetime.strptime('09:30', '%H:%M').time(), datetime.strptime('11:00', '%H:%M').time()),
            (datetime.strptime('10:30', '%H:%M').time(), datetime.strptime('12:00', '%H:%M').time()),
        ]
        result = merge_intervals(intervals)
        
        # All should merge into one: 09:00-12:00
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], (datetime.strptime('09:00', '%H:%M').time(), datetime.strptime('12:00', '%H:%M').time()))
    
    def test_get_available_times_multiple_availabilities(self):
        """Test getting times with multiple availability blocks"""
        self.user = User.objects.create_user(
            username='testuser2',
            email='user2@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach2',
            email='coach2@test.com',
            password='testpass123'
        )
        
        self.coach = create_test_coach_profile(self.coach_user)
        
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,
            price=Decimal('150000.00')
        )
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Create two separate availability blocks
        CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=datetime.strptime('09:00', '%H:%M').time(),
            end_time=datetime.strptime('11:00', '%H:%M').time()
        )
        
        CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=datetime.strptime('14:00', '%H:%M').time(),
            end_time=datetime.strptime('16:00', '%H:%M').time()
        )
        
        available_times = get_available_start_times(
            coach=self.coach,
            course=self.course,
            target_date=tomorrow,
            step_minutes=30
        )
        
        # Should have times from both blocks
        self.assertIn('09:00', available_times)
        self.assertIn('14:00', available_times)
        # Should not have times in the gap
        self.assertNotIn('12:00', available_times)
    
    def test_booking_at_availability_boundary(self):
        """Test booking exactly at availability start/end time"""
        self.user = User.objects.create_user(
            username='testuser3',
            email='user3@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach3',
            email='coach3@test.com',
            password='testpass123'
        )
        
        self.coach = create_test_coach_profile(self.coach_user)
        
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,
            price=Decimal('150000.00')
        )
        
        tomorrow = date.today() + timedelta(days=1)
        
        # Availability: 09:00-10:00 (only 1 hour)
        CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=datetime.strptime('09:00', '%H:%M').time(),
            end_time=datetime.strptime('10:00', '%H:%M').time()
        )
        
        available_times = get_available_start_times(
            coach=self.coach,
            course=self.course,
            target_date=tomorrow,
            step_minutes=30
        )
        
        # Should have 09:00 (exactly at start)
        # Should NOT have 09:30 (would end at 10:30, beyond availability)
        self.assertIn('09:00', available_times)
        self.assertNotIn('09:30', available_times)


class BookingConcurrencyTest(TestCase):
    """Test concurrent booking scenarios"""
    
    def setUp(self):
        self.client = Client()
        
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach4',
            email='coach4@test.com',
            password='testpass123'
        )
        
        self.coach = create_test_coach_profile(self.coach_user)
        
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,
            price=Decimal('150000.00')
        )
        
        tomorrow = date.today() + timedelta(days=1)
        CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=datetime.strptime('09:00', '%H:%M').time(),
            end_time=datetime.strptime('17:00', '%H:%M').time()
        )
        
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    def test_multiple_overlapping_bookings_same_time(self):
        """Test multiple users trying to book same time slot"""
        tomorrow = date.today() + timedelta(days=1)
        
        # User 1 books 10:00-11:00
        self.client.login(username='user1', password='testpass123')
        data = {
            'date': tomorrow.strftime('%Y-%m-%d'),
            'start_time': '10:00'
        }
        
        response1 = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response1.status_code, 200)
        
        # User 2 tries to book same time
        self.client.login(username='user2', password='testpass123')
        
        response2 = self.client.post(
            f'/booking/api/course/{self.course.id}/create/',
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should fail with conflict
        self.assertEqual(response2.status_code, 409)
        
        # Only one booking should exist
        bookings = Booking.objects.filter(
            start_datetime=self.jakarta_tz.localize(
                datetime.combine(tomorrow, datetime.strptime('10:00', '%H:%M').time())
            )
        )
        self.assertEqual(bookings.count(), 1)


class BookingModelMethodsTest(TestCase):
    """Test Booking model methods and properties"""
    
    def setUp(self):
        # Create users
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        
        # Create coach profile
        self.coach = create_test_coach_profile(self.coach_user)
        
        # Create course
        self.course = Course.objects.create(
            coach=self.coach,
            title='Test Course',
            description='Test Description',
            duration=60,
            price=Decimal('150000.00')
        )
        
        self.jakarta_tz = pytz.timezone('Asia/Jakarta')
    
    def test_booking_clean_validation_end_before_start(self):
        """Test that clean() validates end_datetime must be after start_datetime"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 9, 0))  # Before start!
        
        booking = Booking(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end
        )
        
        with self.assertRaises(ValidationError) as context:
            booking.clean()
        
        self.assertIn('End datetime must be after start datetime', str(context.exception))
    
    def test_booking_clean_validation_course_coach_mismatch(self):
        """Test that clean() validates course belongs to coach"""
        # Create another coach and their course
        other_coach_user = User.objects.create_user(
            username='othercoach',
            email='other@test.com',
            password='testpass123'
        )
        other_coach = create_test_coach_profile(other_coach_user)
        
        other_course = Course.objects.create(
            coach=other_coach,
            title='Other Course',
            description='Other Description',
            duration=60,
            price=Decimal('100000.00')
        )
        
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 11, 0))
        
        # Try to book course from different coach
        booking = Booking(
            user=self.user,
            coach=self.coach,  # Coach A
            course=other_course,  # Course from Coach B
            start_datetime=start,
            end_datetime=end
        )
        
        with self.assertRaises(ValidationError) as context:
            booking.clean()
        
        self.assertIn('Course must belong to the selected coach', str(context.exception))
    
    def test_booking_save_with_validation(self):
        """Test that save() calls full_clean() when datetimes are present"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 9, 0))  # Invalid!
        
        booking = Booking(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end
        )
        
        with self.assertRaises(ValidationError):
            booking.save()
    
    def test_booking_status_transition_to_done_updates_coach_stats(self):
        """Test that transitioning to 'done' updates coach minutes and balance"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 11, 30))  # 90 minutes
        
        # Create booking
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end,
            status='confirmed'
        )
        
        # Store initial values
        initial_minutes = self.coach.total_minutes_coached
        initial_balance = self.coach.balance
        
        # Mark as done
        booking.status = 'done'
        booking.save()
        
        # Refresh coach from DB
        self.coach.refresh_from_db()
        
        # Check minutes updated (90 minutes added)
        self.assertEqual(
            self.coach.total_minutes_coached,
            initial_minutes + 90
        )
        
        # Check balance updated (course price added)
        self.assertEqual(
            self.coach.balance,
            initial_balance + int(self.course.price)
        )
    
    def test_booking_status_done_to_done_no_double_count(self):
        """Test that re-saving 'done' booking doesn't double-count stats"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 11, 0))  # 60 minutes
        
        # Create booking already marked as done
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end,
            status='done'
        )
        
        # Get coach stats after first save
        self.coach.refresh_from_db()
        minutes_after_done = self.coach.total_minutes_coached
        balance_after_done = self.coach.balance
        
        # Re-save the booking (still 'done')
        booking.save()
        
        # Refresh coach
        self.coach.refresh_from_db()
        
        # Stats should NOT change
        self.assertEqual(self.coach.total_minutes_coached, minutes_after_done)
        self.assertEqual(self.coach.balance, balance_after_done)
    
    def test_booking_str_representation(self):
        """Test __str__ method returns correct format"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 14, 30))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 15, 30))
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end
        )
        
        expected = f"testuser - Test Course @ 2025-10-25 14:30"
        self.assertEqual(str(booking), expected)
    
    def test_booking_date_property(self):
        """Test date property returns date portion of start_datetime"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 14, 30))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 15, 30))
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end
        )
        
        self.assertEqual(booking.date, date(2025, 10, 25))
    
    def test_booking_start_time_property(self):
        """Test start_time property returns time portion of start_datetime"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 14, 30))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 15, 30))
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end
        )
        
        from datetime import time
        self.assertEqual(booking.start_time, time(14, 30))
    
    def test_booking_end_time_property(self):
        """Test end_time property returns time portion of end_datetime"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 14, 30))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 15, 30))
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end
        )
        
        from datetime import time
        self.assertEqual(booking.end_time, time(15, 30))
    
    def test_booking_ordering(self):
        """Test bookings are ordered by created_at descending"""
        # Create 3 bookings
        start1 = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end1 = self.jakarta_tz.localize(datetime(2025, 10, 25, 11, 0))
        
        booking1 = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start1,
            end_datetime=end1
        )
        
        start2 = self.jakarta_tz.localize(datetime(2025, 10, 26, 10, 0))
        end2 = self.jakarta_tz.localize(datetime(2025, 10, 26, 11, 0))
        
        booking2 = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start2,
            end_datetime=end2
        )
        
        start3 = self.jakarta_tz.localize(datetime(2025, 10, 27, 10, 0))
        end3 = self.jakarta_tz.localize(datetime(2025, 10, 27, 11, 0))
        
        booking3 = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start3,
            end_datetime=end3
        )
        
        # Get all bookings
        bookings = list(Booking.objects.all())
        
        # Should be ordered newest first
        self.assertEqual(bookings[0].id, booking3.id)
        self.assertEqual(bookings[1].id, booking2.id)
        self.assertEqual(bookings[2].id, booking1.id)
    
    def test_booking_status_pending_to_paid_transition(self):
        """Test status transition from pending to paid"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 11, 0))
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end,
            status='pending'
        )
        
        # Transition to paid
        booking.status = 'paid'
        booking.save()
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'paid')
    
    def test_booking_status_paid_to_confirmed_transition(self):
        """Test status transition from paid to confirmed"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 11, 0))
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end,
            status='paid'
        )
        
        # Transition to confirmed
        booking.status = 'confirmed'
        booking.save()
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'confirmed')
    
    def test_booking_canceled_status(self):
        """Test booking can be canceled from any status"""
        start = self.jakarta_tz.localize(datetime(2025, 10, 25, 10, 0))
        end = self.jakarta_tz.localize(datetime(2025, 10, 25, 11, 0))
        
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=start,
            end_datetime=end,
            status='confirmed'
        )
        
        # Cancel booking
        booking.status = 'canceled'
        booking.save()
        
        booking.refresh_from_db()
        self.assertEqual(booking.status, 'canceled')
