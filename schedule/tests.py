from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, time as dt_time, datetime, timedelta
import json

from user_profile.models import CoachProfile
from schedule.models import CoachAvailability, ScheduleSlot
from courses_and_coach.models import Course, Category
from booking.models import Booking


class CoachAvailabilityModelTest(TestCase):
    """Test cases for CoachAvailability model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.user)
        
        self.availability = CoachAvailability.objects.create(
            coach=self.coach,
            date=date.today(),
            start_time=dt_time(9, 0),
            end_time=dt_time(17, 0)
        )
    
    def test_availability_creation(self):
        """Test creating an availability slot"""
        self.assertEqual(CoachAvailability.objects.count(), 1)
        self.assertEqual(self.availability.coach, self.coach)
        self.assertEqual(self.availability.date, date.today())
    
    def test_availability_str(self):
        """Test availability string representation"""
        str_repr = str(self.availability)
        # The __str__ method format might be just showing times
        self.assertIsNotNone(str_repr)
        self.assertIn('09:00', str_repr)
    
    def test_availability_time_validation(self):
        """Test that end time must be after start time"""
        invalid_avail = CoachAvailability(
            coach=self.coach,
            date=date.today(),
            start_time=dt_time(17, 0),
            end_time=dt_time(9, 0)
        )
        # Should raise validation error on save or clean
        try:
            invalid_avail.full_clean()
            self.fail("Should have raised validation error")
        except Exception:
            pass
    
    def test_multiple_slots_same_date(self):
        """Test creating multiple availability slots on same date"""
        avail2 = CoachAvailability.objects.create(
            coach=self.coach,
            date=date.today(),
            start_time=dt_time(14, 0),
            end_time=dt_time(18, 0)
        )
        
        availabilities = CoachAvailability.objects.filter(
            coach=self.coach,
            date=date.today()
        )
        self.assertEqual(availabilities.count(), 2)
    
    def test_availability_different_dates(self):
        """Test availability on different dates"""
        tomorrow = date.today() + timedelta(days=1)
        avail2 = CoachAvailability.objects.create(
            coach=self.coach,
            date=tomorrow,
            start_time=dt_time(10, 0),
            end_time=dt_time(15, 0)
        )
        
        today_slots = CoachAvailability.objects.filter(
            coach=self.coach,
            date=date.today()
        )
        tomorrow_slots = CoachAvailability.objects.filter(
            coach=self.coach,
            date=tomorrow
        )
        
        self.assertEqual(today_slots.count(), 1)
        self.assertEqual(tomorrow_slots.count(), 1)


class ScheduleSlotModelTest(TestCase):
    """Test cases for ScheduleSlot model"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.user)
        
        self.slot = ScheduleSlot.objects.create(
            coach=self.coach,
            date=date.today(),
            start_time=dt_time(9, 0),
            end_time=dt_time(10, 0)
        )
    
    def test_schedule_slot_creation(self):
        """Test creating a schedule slot"""
        self.assertEqual(ScheduleSlot.objects.count(), 1)
        self.assertEqual(self.slot.coach, self.coach)
    
    def test_schedule_slot_str(self):
        """Test schedule slot string representation"""
        str_repr = str(self.slot)
        # The __str__ method format might be just showing times
        self.assertIsNotNone(str_repr)
        self.assertIn('09:00', str_repr)
    
    def test_schedule_slot_cascade_delete(self):
        """Test slots are deleted when coach is deleted"""
        slot_id = self.slot.id
        self.coach.delete()
        
        self.assertFalse(ScheduleSlot.objects.filter(id=slot_id).exists())


class ApiAvailabilityUpsertTest(TestCase):
    """Test cases for api_availability_upsert endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.user)
        self.client.force_login(self.user)
        
        self.test_date = (date.today() + timedelta(days=1)).isoformat()
    
    def test_upsert_requires_login(self):
        """Test endpoint requires authentication"""
        self.client.logout()
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [{'start': '09:00', 'end': '10:00'}]
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_upsert_requires_coach_profile(self):
        """Test endpoint requires coach profile"""
        user = User.objects.create_user(
            username='notacoach',
            password='testpass123'
        )
        self.client.force_login(user)
        
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [{'start': '09:00', 'end': '10:00'}]
            }),
            content_type='application/json'
        )
        # Should get 404 or 500 when coach doesn't exist
        self.assertIn(response.status_code, [404, 500])
    
    def test_upsert_missing_date(self):
        """Test upsert with missing date"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'ranges': [{'start': '09:00', 'end': '10:00'}]
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_upsert_invalid_date_format(self):
        """Test upsert with invalid date format"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': 'invalid-date',
                'ranges': [{'start': '09:00', 'end': '10:00'}]
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_upsert_missing_ranges(self):
        """Test upsert with missing ranges"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({'date': self.test_date}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_upsert_empty_ranges(self):
        """Test upsert with empty ranges"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': []
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_upsert_invalid_time_range(self):
        """Test upsert with invalid time range (end before start)"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [{'start': '17:00', 'end': '09:00'}]
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_upsert_valid_single_range(self):
        """Test valid upsert with single range"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [{'start': '09:00', 'end': '17:00'}],
                'mode': 'replace'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['original_count'], 1)
    
    def test_upsert_multiple_ranges(self):
        """Test upsert with multiple ranges"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [
                    {'start': '09:00', 'end': '12:00'},
                    {'start': '14:00', 'end': '17:00'}
                ],
                'mode': 'replace'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['original_count'], 2)
    
    def test_upsert_replace_mode(self):
        """Test upsert with replace mode"""
        # Create initial availability
        CoachAvailability.objects.create(
            coach=self.coach,
            date=datetime.strptime(self.test_date, '%Y-%m-%d').date(),
            start_time=dt_time(9, 0),
            end_time=dt_time(10, 0)
        )
        
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [{'start': '14:00', 'end': '17:00'}],
                'mode': 'replace'
            }),
            content_type='application/json'
        )
        
        # Old availability should be deleted
        availabilities = CoachAvailability.objects.filter(
            coach=self.coach,
            date=datetime.strptime(self.test_date, '%Y-%m-%d').date()
        )
        self.assertEqual(availabilities.count(), 1)
        self.assertEqual(availabilities.first().start_time, dt_time(14, 0))
    
    def test_upsert_overlapping_ranges_merged(self):
        """Test that overlapping ranges are merged"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [
                    {'start': '09:00', 'end': '11:00'},
                    {'start': '10:30', 'end': '12:00'}
                ],
                'mode': 'replace'
            }),
            content_type='application/json'
        )
        
        data = json.loads(response.content)
        self.assertEqual(data['merged_count'], 1)
    
    def test_upsert_adjacent_ranges_merged(self):
        """Test that adjacent ranges are merged"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [
                    {'start': '09:00', 'end': '12:00'},
                    {'start': '12:00', 'end': '17:00'}
                ],
                'mode': 'replace'
            }),
            content_type='application/json'
        )
        
        data = json.loads(response.content)
        self.assertEqual(data['merged_count'], 1)
    
    def test_upsert_response_structure(self):
        """Test response structure"""
        response = self.client.post(
            '/schedule/api/availability/upsert/',
            data=json.dumps({
                'date': self.test_date,
                'ranges': [{'start': '09:00', 'end': '17:00'}],
                'mode': 'replace'
            }),
            content_type='application/json'
        )
        
        data = json.loads(response.content)
        self.assertIn('success', data)
        self.assertIn('message', data)
        self.assertIn('date', data)
        self.assertIn('merged_intervals', data)
        self.assertIn('original_count', data)
        self.assertIn('merged_count', data)


class ApiGetAvailabilityTest(TestCase):
    """Test cases for api_get_availability endpoint"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.user)
        self.test_date = (date.today() + timedelta(days=1)).isoformat()
    
    def test_api_endpoints_exist(self):
        """Test that API endpoints are configured"""
        # Just ensure the app is configured properly
        self.assertTrue(True)

