from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import CoachProfile, Certification, UserProfile
from courses_and_coach.models import Category, Course
from booking.models import Booking
from schedule.models import ScheduleSlot
from reviews.models import Review
from chat.models import ChatSession
import json
from datetime import datetime, timedelta
from django.utils import timezone


class RegisterUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('user_profile:register')
    
    def test_register_user_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
    
    def test_register_user_authenticated_redirect(self):
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 302)
    
    def test_register_user_post_success(self):
        data = {
            'username': 'newuser',
            'first_name': 'New',
            'last_name': 'User',
            'email': 'newuser@test.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        }
        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        self.assertTrue(UserProfile.objects.filter(user__username='newuser').exists())
    
    def test_register_user_ajax_success(self):
        data = {
            'username': 'ajaxuser',
            'first_name': 'Ajax',
            'last_name': 'User',
            'email': 'ajax@test.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        }
        response = self.client.post(
            self.register_url, 
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
    
    def test_register_user_ajax_failure(self):
        data = {
            'username': 'bad',
            'password1': 'pass',
            'password2': 'different'
        }
        response = self.client.post(
            self.register_url,
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
        json_response = json.loads(response.content)
        self.assertFalse(json_response['success'])


class RegisterCoachViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_coach_url = reverse('user_profile:register_coach')
        self.category = Category.objects.create(
            name='Fitness',
            description='Fitness coaching'
        )
    
    def test_register_coach_get(self):
        response = self.client.get(self.register_coach_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register_coach.html')
    
    def test_register_coach_authenticated_redirect(self):
        user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.register_coach_url)
        self.assertEqual(response.status_code, 302)
    
    def test_register_coach_success(self):
        data = {
            'username': 'coachuser',
            'first_name': 'Coach',
            'last_name': 'Test',
            'email': 'coach@test.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'bio': 'I am a fitness coach',
            'expertise[]': [str(self.category.id)],
            'certification_name[]': ['Cert 1'],
            'certification_url[]': ['http://cert1.com']
        }
        response = self.client.post(self.register_coach_url, data)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='coachuser').exists())
        self.assertTrue(CoachProfile.objects.filter(user__username='coachuser').exists())
    
    def test_register_coach_no_expertise(self):
        data = {
            'username': 'coachuser',
            'first_name': 'Coach',
            'last_name': 'Test',
            'email': 'coach@test.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'bio': 'I am a fitness coach',
        }
        response = self.client.post(self.register_coach_url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CoachProfile.objects.filter(user__username='coachuser').exists())
    
    def test_register_coach_ajax_success(self):
        data = {
            'username': 'ajaxcoach',
            'first_name': 'Ajax',
            'last_name': 'Coach',
            'email': 'ajaxcoach@test.com',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!',
            'bio': 'Ajax coach bio',
            'expertise[]': [str(self.category.id)]
        }
        response = self.client.post(
            self.register_coach_url,
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])


class LoginUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.login_url = reverse('user_profile:login')
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
    
    def test_login_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')
    
    def test_login_authenticated_redirect(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 302)
    
    def test_login_success(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
    
    def test_login_ajax_success(self):
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'testpass123'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
    
    def test_login_ajax_failure(self):
        response = self.client.post(
            self.login_url,
            {'username': 'testuser', 'password': 'wrongpass'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
        json_response = json.loads(response.content)
        self.assertFalse(json_response['success'])
    
    def test_login_failure(self):
        response = self.client.post(self.login_url, {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)


class LogoutUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.logout_url = reverse('user_profile:logout')
        self.user = User.objects.create_user(username='testuser', password='testpass123')
    
    def test_logout_success(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.logout_url)
        self.assertEqual(response.status_code, 302)
    
    def test_logout_ajax_success(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            self.logout_url,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])


class DashboardCoachViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('user_profile:dashboard_coach')
        self.coach_user = User.objects.create_user(
            username='coach',
            password='testpass123',
            first_name='Coach',
            last_name='Test'
        )
        self.coach_profile = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Test coach bio',
            expertise=['Fitness']
        )
        self.regular_user = User.objects.create_user(
            username='regular',
            password='testpass123'
        )
    
    def test_dashboard_coach_not_authenticated(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_coach_authenticated_coach(self):
        self.client.login(username='coach', password='testpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard_coach.html')
    
    def test_dashboard_coach_not_a_coach(self):
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)


class GetCoachProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.get_profile_url = reverse('user_profile:get_coach_profile')
        self.coach_user = User.objects.create_user(
            username='coach',
            password='testpass123',
            first_name='Coach',
            last_name='Test'
        )
        self.coach_profile = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Test coach bio',
            expertise=['Fitness'],
            rating=4.5
        )
        self.category = Category.objects.create(name='Fitness')
        self.course = Course.objects.create(
            coach=self.coach_profile,
            title='Test Course',
            description='Test Description',
            price=100000,
            duration=60,
            category=self.category
        )
        self.regular_user = User.objects.create_user(username='regular', password='testpass123')
    
    def test_get_coach_profile_success(self):
        self.client.login(username='coach', password='testpass123')
        response = self.client.get(self.get_profile_url)
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])
        self.assertEqual(json_response['profile']['rating'], 4.5)
    
    def test_get_coach_profile_not_coach(self):
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(self.get_profile_url)
        self.assertEqual(response.status_code, 403)


class CoachProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile_url = reverse('user_profile:coach_profile')
        self.coach_user = User.objects.create_user(
            username='coach',
            password='testpass123',
            first_name='Coach',
            last_name='Test'
        )
        self.coach_profile = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Test coach bio',
            expertise=['Fitness']
        )
        self.category = Category.objects.create(name='Fitness')
    
    def test_coach_profile_get(self):
        self.client.login(username='coach', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'coach_profile.html')
    
    def test_coach_profile_update(self):
        self.client.login(username='coach', password='testpass123')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'bio': 'Updated bio',
            'expertise[]': [str(self.category.id)],
            'new_cert_names[]': ['New Cert'],
            'new_cert_urls[]': ['http://newcert.com']
        }
        response = self.client.post(self.profile_url, data)
        self.assertEqual(response.status_code, 302)
        self.coach_user.refresh_from_db()
        self.assertEqual(self.coach_user.first_name, 'Updated')


class DashboardUserViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.dashboard_url = reverse('user_profile:dashboard_user')
        self.user = User.objects.create_user(
            username='user',
            password='testpass123'
        )
        self.coach_user = User.objects.create_user(
            username='coach',
            password='testpass123'
        )
        self.coach_profile = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Test'
        )
    
    def test_dashboard_user_not_authenticated(self):
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_user_authenticated(self):
        self.client.login(username='user', password='testpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard_user.html')
    
    def test_dashboard_user_coach_redirect(self):
        self.client.login(username='coach', password='testpass123')
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 302)


class GetUserProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.get_profile_url = reverse('user_profile:get_user_profile')
        self.user = User.objects.create_user(
            username='user',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.user_profile = UserProfile.objects.create(user=self.user)
    
    def test_get_user_profile_success(self):
        self.client.login(username='user', password='testpass123')
        response = self.client.get(self.get_profile_url)
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])


class UserProfileViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.profile_url = reverse('user_profile:user_profile')
        self.user = User.objects.create_user(
            username='user',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.user_profile = UserProfile.objects.create(user=self.user)
    
    def test_user_profile_get(self):
        self.client.login(username='user', password='testpass123')
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_profile.html')
    
    def test_user_profile_update(self):
        self.client.login(username='user', password='testpass123')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.post(self.profile_url, data)
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')
    
    def test_user_profile_ajax_update(self):
        self.client.login(username='user', password='testpass123')
        data = {
            'first_name': 'Ajax',
            'last_name': 'Update'
        }
        response = self.client.post(
            self.profile_url,
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        json_response = json.loads(response.content)
        self.assertTrue(json_response['success'])


class FormTests(TestCase):
    """Test cases for user_profile forms"""
    
    def setUp(self):
        """Set up test fixtures"""
        from courses_and_coach.models import Category
        self.category = Category.objects.create(name='Fitness')
    
    def test_trainee_registration_form_valid(self):
        """Test TraineeRegistrationForm with valid data"""
        from user_profile.forms import TraineeRegistrationForm
        data = {
            'username': 'newtrainee',
            'first_name': 'New',
            'last_name': 'Trainee',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        }
        form = TraineeRegistrationForm(data)
        self.assertTrue(form.is_valid())
    
    def test_trainee_registration_form_passwords_mismatch(self):
        """Test TraineeRegistrationForm with mismatched passwords"""
        from user_profile.forms import TraineeRegistrationForm
        data = {
            'username': 'newtrainee',
            'first_name': 'New',
            'last_name': 'Trainee',
            'password1': 'ComplexPass123!',
            'password2': 'DifferentPass123!'
        }
        form = TraineeRegistrationForm(data)
        self.assertFalse(form.is_valid())
    
    def test_coach_registration_form_valid(self):
        """Test CoachRegistrationForm with valid data"""
        from user_profile.forms import CoachRegistrationForm
        data = {
            'username': 'newcoach',
            'first_name': 'New',
            'last_name': 'Coach',
            'bio': 'I am a certified fitness coach',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        }
        form = CoachRegistrationForm(data)
        self.assertTrue(form.is_valid())
    
    def test_coach_registration_form_save(self):
        """Test CoachRegistrationForm save method"""
        from user_profile.forms import CoachRegistrationForm
        data = {
            'username': 'newcoach',
            'first_name': 'New',
            'last_name': 'Coach',
            'bio': 'I am a certified fitness coach',
            'password1': 'ComplexPass123!',
            'password2': 'ComplexPass123!'
        }
        form = CoachRegistrationForm(data)
        self.assertTrue(form.is_valid())
        user = form.save()
        
        # Verify user was created
        self.assertEqual(user.username, 'newcoach')
        self.assertEqual(user.first_name, 'New')
        self.assertEqual(user.last_name, 'Coach')
    
    def test_get_sport_choices(self):
        """Test get_sport_choices function returns categories"""
        from user_profile.forms import get_sport_choices
        choices = get_sport_choices()
        
        # Should return list of tuples
        self.assertIsInstance(choices, list)
        self.assertEqual(len(choices), 1)
        self.assertEqual(choices[0], ('Fitness', 'Fitness'))


class UserProfileModelTests(TestCase):
    """Test UserProfile model properties"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )
        self.profile = UserProfile.objects.create(user=self.user)
    
    def test_user_profile_str(self):
        """Test UserProfile string representation"""
        self.assertEqual(str(self.profile), "testuser's Profile")
    
    def test_user_profile_image_url_default(self):
        """Test image_url returns avatar placeholder when no image"""
        url = self.profile.image_url
        self.assertIn('ui-avatars.com', url)
        self.assertIn('Test User', url)  # Full name in URL
    
    def test_user_profile_image_url_with_url(self):
        """Test image_url returns profile_image_url when set"""
        test_url = 'https://example.com/photo.jpg'
        self.profile.profile_image_url = test_url
        self.profile.save()
        self.assertEqual(self.profile.image_url, test_url)


class CoachProfileModelTests(TestCase):
    """Test CoachProfile model properties"""
    
    def setUp(self):
        self.coach_user = User.objects.create_user(
            username='testcoach',
            email='coach@test.com',
            password='testpass123',
            first_name='Coach',
            last_name='Test'
        )
        self.coach = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Professional coach'
        )
    
    def test_coach_profile_str(self):
        """Test CoachProfile string representation"""
        self.assertEqual(str(self.coach), 'testcoach - Coach')
    
    def test_coach_profile_image_url_default(self):
        """Test image_url returns avatar placeholder when no image"""
        url = self.coach.image_url
        self.assertIn('ui-avatars.com', url)
        self.assertIn('Coach Test', url)
    
    def test_coach_profile_image_url_with_url(self):
        """Test image_url returns profile_image_url when set"""
        test_url = 'https://example.com/coach.jpg'
        self.coach.profile_image_url = test_url
        self.coach.save()
        self.assertEqual(self.coach.image_url, test_url)
    
    def test_total_hours_coached_property(self):
        """Test total_hours_coached property"""
        self.coach.total_minutes_coached = 120  # 2 hours
        self.coach.save()
        self.assertEqual(self.coach.total_hours_coached, 2.0)
    
    def test_total_hours_coached_formatted_integer(self):
        """Test total_hours_coached_formatted with whole hours"""
        self.coach.total_minutes_coached = 180  # 3 hours
        self.coach.save()
        self.assertEqual(self.coach.total_hours_coached_formatted, '3 jam')
    
    def test_total_hours_coached_formatted_decimal(self):
        """Test total_hours_coached_formatted with decimal hours"""
        self.coach.total_minutes_coached = 90  # 1.5 hours
        self.coach.save()
        self.assertEqual(self.coach.total_hours_coached_formatted, '1.5 jam')
    
    def test_balance_formatted(self):
        """Test balance_formatted with thousand separators"""
        self.coach.balance = 1000000
        self.coach.save()
        self.assertEqual(self.coach.balance_formatted, '1,000,000')
