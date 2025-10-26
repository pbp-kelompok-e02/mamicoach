"""
Comprehensive test cases for admin_panel module to achieve 90%+ coverage
"""
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.hashers import check_password
from .models import AdminUser, AdminSettings, AdminActivityLog
from django.utils import timezone
from django.contrib.auth.models import User as DjangoUser
from courses_and_coach.models import Course, Category
from user_profile.models import UserProfile, CoachProfile, AdminVerification
from payment.models import Payment
from booking.models import Booking
from datetime import timedelta


class AdminLoginViewTest(TestCase):
    """Test admin login view"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='testadmin',
            email='admin@test.com',
            is_active=True
        )
        self.admin_user.set_password('testpass123')
        self.admin_user.save()
        
        self.inactive_admin = AdminUser.objects.create(
            username='inactive',
            email='inactive@test.com',
            is_active=False
        )
        self.inactive_admin.set_password('testpass123')
        self.inactive_admin.save()
    
    def test_login_get_returns_form(self):
        """Test GET returns login form"""
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/login.html')
    
    def test_login_valid_credentials(self):
        """Test login with valid credentials"""
        response = self.client.post('/admin/login/', {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn('admin_user_id', self.client.session)
    
    def test_login_invalid_password(self):
        """Test login with invalid password"""
        response = self.client.post('/admin/login/', {
            'username': 'testadmin',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('admin_user_id', self.client.session)
    
    def test_login_nonexistent_user(self):
        """Test login with non-existent user"""
        response = self.client.post('/admin/login/', {
            'username': 'nonexistent',
            'password': 'anypass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('admin_user_id', self.client.session)
    
    def test_login_inactive_user(self):
        """Test login with inactive user"""
        response = self.client.post('/admin/login/', {
            'username': 'inactive',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('admin_user_id', self.client.session)
    
    def test_login_updates_last_login(self):
        """Test login updates last_login"""
        before = timezone.now()
        self.client.post('/admin/login/', {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        after = timezone.now()
        
        self.admin_user.refresh_from_db()
        self.assertIsNotNone(self.admin_user.last_login)
        self.assertGreaterEqual(self.admin_user.last_login, before)
        self.assertLessEqual(self.admin_user.last_login, after)
    
    def test_login_logs_activity(self):
        """Test login is logged"""
        self.client.post('/admin/login/', {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        
        log = AdminActivityLog.objects.filter(
            admin_user=self.admin_user,
            action='login'
        ).first()
        self.assertIsNotNone(log)
    
    def test_login_redirects_if_already_logged_in(self):
        """Test GET redirects if already logged in"""
        self.client.post('/admin/login/', {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        response = self.client.get('/admin/login/')
        self.assertEqual(response.status_code, 302)


class AdminLogoutViewTest(TestCase):
    """Test admin logout view"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='testadmin',
            email='admin@test.com'
        )
        self.admin_user.set_password('testpass123')
        self.admin_user.save()
    
    def test_logout_requires_login(self):
        """Test logout requires login"""
        response = self.client.get('/admin/logout/')
        self.assertEqual(response.status_code, 302)
    
    def test_logout_clears_session(self):
        """Test logout clears session"""
        self.client.post('/admin/login/', {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        self.assertIn('admin_user_id', self.client.session)
        self.client.get('/admin/logout/')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
    
    def test_logout_logs_activity(self):
        """Test logout is logged"""
        self.client.post('/admin/login/', {
            'username': 'testadmin',
            'password': 'testpass123'
        })
        self.client.get('/admin/logout/')
        
        log = AdminActivityLog.objects.filter(
            admin_user=self.admin_user,
            action='logout'
        ).first()
        self.assertIsNotNone(log)


class AdminDashboardViewTest(TestCase):
    """Test admin dashboard view"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        django_user = DjangoUser.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='pass123'
        )
        UserProfile.objects.create(user=django_user)
        
        coach_user = DjangoUser.objects.create_user(
            username='coach',
            email='coach@test.com',
            password='pass123'
        )
        self.coach = CoachProfile.objects.create(user=coach_user)
        
        self.category = Category.objects.create(name='Fitness')
        self.course = Course.objects.create(
            title='Test Course',
            coach=self.coach,
            price=100000,
            duration=60
        )
        
        self.booking = Booking.objects.create(
            user=django_user,
            coach=self.coach,
            course=self.course,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
            status='pending'
        )
        
        self.payment = Payment.objects.create(
            booking=self.booking,
            user=django_user,
            amount=100000,
            order_id='test-order-123',
            status='settlement'
        )
    
    def test_dashboard_requires_login(self):
        """Test dashboard requires login"""
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 302)
    
    def test_dashboard_displays_statistics(self):
        """Test dashboard displays statistics"""
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/dashboard.html')
        
        context = response.context
        self.assertEqual(context['total_users'], 1)
        self.assertEqual(context['total_coaches'], 1)
        self.assertEqual(context['total_courses'], 1)
        self.assertEqual(context['total_bookings'], 1)
    
    def test_dashboard_calculates_revenue(self):
        """Test dashboard calculates revenue"""
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        response = self.client.get('/admin/')
        context = response.context
        self.assertEqual(context['total_revenue'], 100000)
    
    def test_dashboard_booking_status_counts(self):
        """Test dashboard booking status counts"""
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        django_user = DjangoUser.objects.get(username='testuser')
        coach = CoachProfile.objects.get(user__username='coach')
        course = Course.objects.get(title='Test Course')
        
        Booking.objects.create(
            user=django_user,
            coach=coach,
            course=course,
            start_datetime=timezone.now() + timedelta(days=2),
            end_datetime=timezone.now() + timedelta(days=2, hours=1),
            status='confirmed'
        )
        Booking.objects.create(
            user=django_user,
            coach=coach,
            course=course,
            start_datetime=timezone.now() + timedelta(days=3),
            end_datetime=timezone.now() + timedelta(days=3, hours=1),
            status='done'
        )
        
        response = self.client.get('/admin/')
        context = response.context
        
        self.assertEqual(context['pending_bookings'], 1)
        self.assertEqual(context['confirmed_bookings'], 1)
        self.assertEqual(context['done_bookings'], 1)


class AdminManagementViewsTest(TestCase):
    """Test management views"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
    
    def test_users_management_view(self):
        """Test users management page"""
        response = self.client.get('/admin/users/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/users.html')
    
    def test_coaches_management_view(self):
        """Test coaches management page"""
        response = self.client.get('/admin/coaches/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/coaches.html')
    
    def test_courses_management_view(self):
        """Test courses management page"""
        response = self.client.get('/admin/courses/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/courses.html')
    
    def test_bookings_management_view(self):
        """Test bookings management page"""
        response = self.client.get('/admin/bookings/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/bookings.html')
    
    def test_payments_management_view(self):
        """Test payments management page"""
        response = self.client.get('/admin/payments/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/payments.html')
    
    def test_management_views_require_login(self):
        """Test management views require login"""
        self.client.logout()
        
        urls = [
            '/admin/users/',
            '/admin/coaches/',
            '/admin/courses/',
            '/admin/bookings/',
            '/admin/payments/',
        ]
        
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)


class AdminSettingsViewTest(TestCase):
    """Test settings management"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
    
    def test_settings_get_view(self):
        """Test settings GET view"""
        response = self.client.get('/admin/settings/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/settings.html')
    
    def test_settings_add_action(self):
        """Test adding setting"""
        response = self.client.post('/admin/settings/', {
            'action': 'add',
            'module': 'payment',
            'key': 'commission_rate',
            'value': '0.1'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            AdminSettings.objects.filter(
                module='payment',
                key='commission_rate',
                value='0.1'
            ).exists()
        )
    
    def test_settings_update_action(self):
        """Test updating setting"""
        setting = AdminSettings.objects.create(
            module='payment',
            key='commission_rate',
            value='0.1',
            updated_by=self.admin_user
        )
        
        response = self.client.post('/admin/settings/', {
            'action': 'update',
            'setting_id': setting.id,
            'value': '0.15'
        })
        
        self.assertEqual(response.status_code, 302)
        setting.refresh_from_db()
        self.assertEqual(setting.value, '0.15')
    
    def test_settings_delete_action(self):
        """Test deleting setting"""
        setting = AdminSettings.objects.create(
            module='payment',
            key='commission_rate',
            value='0.1',
            updated_by=self.admin_user
        )
        
        setting_id = setting.id
        response = self.client.post('/admin/settings/', {
            'action': 'delete',
            'setting_id': setting_id
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(AdminSettings.objects.filter(id=setting_id).exists())
    
    def test_settings_logs_add_activity(self):
        """Test add activity is logged"""
        self.client.post('/admin/settings/', {
            'action': 'add',
            'module': 'payment',
            'key': 'new_setting',
            'value': 'test'
        })
        
        log = AdminActivityLog.objects.filter(
            admin_user=self.admin_user,
            action='create',
            module='settings'
        ).first()
        self.assertIsNotNone(log)
    
    def test_settings_logs_update_activity(self):
        """Test update activity is logged"""
        setting = AdminSettings.objects.create(
            module='payment',
            key='test_key',
            value='old_value',
            updated_by=self.admin_user
        )
        
        self.client.post('/admin/settings/', {
            'action': 'update',
            'setting_id': setting.id,
            'value': 'new_value'
        })
        
        log = AdminActivityLog.objects.filter(
            admin_user=self.admin_user,
            action='update',
            module='settings'
        ).first()
        self.assertIsNotNone(log)


class AdminActivityLogsViewTest(TestCase):
    """Test activity logs view"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        AdminActivityLog.objects.create(
            admin_user=self.admin_user,
            action='login',
            module='auth',
            description='Test login'
        )
        AdminActivityLog.objects.create(
            admin_user=self.admin_user,
            action='view',
            module='dashboard',
            description='Test view'
        )
    
    def test_logs_view_all_actions(self):
        """Test logs page displays all actions"""
        response = self.client.get('/admin/logs/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/logs.html')
        self.assertGreaterEqual(len(response.context['logs']), 2)
    
    def test_logs_filter_by_action(self):
        """Test logs page filters by action"""
        response = self.client.get('/admin/logs/?action=login')
        self.assertEqual(response.status_code, 200)
        
        logs = response.context['logs']
        self.assertTrue(all(log.action == 'login' for log in logs))
    
    def test_logs_requires_login(self):
        """Test logs page requires login"""
        self.client.logout()
        response = self.client.get('/admin/logs/')
        self.assertEqual(response.status_code, 302)


class AdminChangePasswordViewTest(TestCase):
    """Test change password view"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('oldpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'oldpass123'
        })
    
    def test_change_password_get_view(self):
        """Test GET returns form"""
        response = self.client.get('/admin/change-password/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_panel/change_password.html')
    
    def test_change_password_with_correct_old_password(self):
        """Test changing password with correct old password"""
        response = self.client.post('/admin/change-password/', {
            'old_password': 'oldpass123',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        })
        
        self.assertEqual(response.status_code, 302)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.check_password('newpass123'))
    
    def test_change_password_with_incorrect_old_password(self):
        """Test changing password with incorrect old password"""
        response = self.client.post('/admin/change-password/', {
            'old_password': 'wrongpass',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        })
        
        self.assertEqual(response.status_code, 302)
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.check_password('oldpass123'))
    
    def test_change_password_mismatched_new_passwords(self):
        """Test changing password with mismatched new passwords"""
        response = self.client.post('/admin/change-password/', {
            'old_password': 'oldpass123',
            'new_password1': 'newpass123',
            'new_password2': 'differentpass123'
        })
        
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.check_password('oldpass123'))
    
    def test_change_password_too_short(self):
        """Test changing password to short password"""
        response = self.client.post('/admin/change-password/', {
            'old_password': 'oldpass123',
            'new_password1': 'short',
            'new_password2': 'short'
        })
        
        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.check_password('oldpass123'))
    
    def test_change_password_requires_login(self):
        """Test change password requires login"""
        self.client.logout()
        response = self.client.get('/admin/change-password/')
        self.assertEqual(response.status_code, 302)


class AdminCoachVerifyViewTest(TestCase):
    """Test coach verification views"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        coach_user = DjangoUser.objects.create_user(
            username='coach',
            email='coach@test.com',
            password='pass123'
        )
        self.coach = CoachProfile.objects.create(user=coach_user, verified=False)
    
    def test_coach_verify_badge(self):
        """Test adding verified badge"""
        response = self.client.post(
            f'/admin/coach/{self.coach.id}/verify/',
            {'action': 'verify'}
        )
        
        self.assertEqual(response.status_code, 302)
        self.coach.refresh_from_db()
        self.assertTrue(self.coach.verified)
    
    def test_coach_unverify_badge(self):
        """Test removing verified badge"""
        self.coach.verified = True
        self.coach.save()
        
        response = self.client.post(
            f'/admin/coach/{self.coach.id}/verify/',
            {'action': 'unverify'}
        )
        
        self.assertEqual(response.status_code, 302)
        self.coach.refresh_from_db()
        self.assertFalse(self.coach.verified)
    
    def test_coach_verify_logs_activity(self):
        """Test coach verification is logged"""
        self.client.post(
            f'/admin/coach/{self.coach.id}/verify/',
            {'action': 'verify'}
        )
        
        log = AdminActivityLog.objects.filter(
            admin_user=self.admin_user,
            action='update',
            module='coaches'
        ).first()
        self.assertIsNotNone(log)


class AdminCoachVerificationDetailViewTest(TestCase):
    """Test coach verification detail view"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        coach_user = DjangoUser.objects.create_user(
            username='coach',
            email='coach@test.com',
            password='pass123'
        )
        self.coach = CoachProfile.objects.create(user=coach_user, verified=False)
    
    def test_coach_verification_detail_page(self):
        """Test coach verification detail page loads"""
        response = self.client.get(f'/admin/coach/{self.coach.id}/verification/')
        self.assertEqual(response.status_code, 200)
    
    def test_coach_approve_action(self):
        """Test approving a coach"""
        response = self.client.post(
            f'/admin/coach/{self.coach.id}/verification/',
            {'action': 'approve', 'notes': 'Approved'}
        )
        
        self.assertEqual(response.status_code, 302)
        self.coach.refresh_from_db()
        self.assertTrue(self.coach.verified)
    
    def test_coach_reject_action(self):
        """Test rejecting a coach"""
        response = self.client.post(
            f'/admin/coach/{self.coach.id}/verification/',
            {'action': 'reject', 'notes': 'Rejected'}
        )
        
        self.assertEqual(response.status_code, 302)
    
    def test_coach_pending_action(self):
        """Test setting coach to pending"""
        AdminVerification.objects.create(
            coach=self.coach,
            status='approved'
        )
        
        response = self.client.post(
            f'/admin/coach/{self.coach.id}/verification/',
            {'action': 'pending', 'notes': 'Pending review'}
        )
        
        self.assertEqual(response.status_code, 302)
    
    def test_coach_toggle_verified_action(self):
        """Test toggling verified badge"""
        response = self.client.post(
            f'/admin/coach/{self.coach.id}/verification/',
            {'action': 'toggle_verified'}
        )
        
        self.assertEqual(response.status_code, 302)
        self.coach.refresh_from_db()
        self.assertTrue(self.coach.verified)


class AdminDeleteViewsTest(TestCase):
    """Test delete views"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        self.user = DjangoUser.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='pass123'
        )
        UserProfile.objects.create(user=self.user)
        
        coach_user = DjangoUser.objects.create_user(
            username='coach',
            email='coach@test.com',
            password='pass123'
        )
        self.coach = CoachProfile.objects.create(user=coach_user)
        
        self.category = Category.objects.create(name='Fitness')
        self.course = Course.objects.create(
            title='Test Course',
            coach=self.coach,
            price=100000,
            duration=60
        )
        
        self.booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
            status='pending'
        )
    
    def test_coach_delete_get_confirmation_page(self):
        """Test coach delete confirmation page"""
        response = self.client.get(f'/admin/coach/{self.coach.id}/delete/')
        self.assertEqual(response.status_code, 200)
    
    def test_coach_delete_post(self):
        """Test deleting a coach"""
        coach_id = self.coach.id
        coach_user_id = self.coach.user.id
        
        response = self.client.post(f'/admin/coach/{coach_id}/delete/')
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(CoachProfile.objects.filter(id=coach_id).exists())
        self.assertFalse(DjangoUser.objects.filter(id=coach_user_id).exists())
    
    def test_user_delete_get_confirmation_page(self):
        """Test user delete confirmation page"""
        response = self.client.get(f'/admin/user/{self.user.id}/delete/')
        self.assertEqual(response.status_code, 200)
    
    def test_user_delete_post(self):
        """Test deleting a user"""
        user_id = self.user.id
        
        response = self.client.post(f'/admin/user/{user_id}/delete/')
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(DjangoUser.objects.filter(id=user_id).exists())
    
    def test_course_delete_get_confirmation_page(self):
        """Test course delete confirmation page"""
        response = self.client.get(f'/admin/course/{self.course.id}/delete/')
        self.assertEqual(response.status_code, 200)
    
    def test_course_delete_post(self):
        """Test deleting a course"""
        course_id = self.course.id
        
        response = self.client.post(f'/admin/course/{course_id}/delete/')
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Course.objects.filter(id=course_id).exists())
    
    def test_booking_delete_get_confirmation_page(self):
        """Test booking delete confirmation page"""
        response = self.client.get(f'/admin/booking/{self.booking.id}/delete/')
        self.assertEqual(response.status_code, 200)
    
    def test_booking_delete_post(self):
        """Test deleting a booking"""
        booking_id = self.booking.id
        
        response = self.client.post(f'/admin/booking/{booking_id}/delete/')
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Booking.objects.filter(id=booking_id).exists())


class AdminBookingUpdateViewTest(TestCase):
    """Test booking update status view"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        user = DjangoUser.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='pass123'
        )
        
        coach_user = DjangoUser.objects.create_user(
            username='coach',
            email='coach@test.com',
            password='pass123'
        )
        coach = CoachProfile.objects.create(user=coach_user)
        
        category = Category.objects.create(name='Fitness')
        course = Course.objects.create(
            title='Test Course',
            coach=coach,
            price=100000,
            duration=60
        )
        
        self.booking = Booking.objects.create(
            user=user,
            coach=coach,
            course=course,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
            status='pending'
        )
    
    def test_booking_update_status_pending_to_confirmed(self):
        """Test updating booking status to confirmed"""
        response = self.client.post(
            f'/admin/booking/{self.booking.id}/update-status/',
            {'status': 'confirmed'}
        )
        
        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'confirmed')
    
    def test_booking_update_status_to_done(self):
        """Test updating booking status to done"""
        response = self.client.post(
            f'/admin/booking/{self.booking.id}/update-status/',
            {'status': 'done'}
        )
        
        self.assertEqual(response.status_code, 302)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'done')
    
    def test_booking_update_status_logs_activity(self):
        """Test booking status update is logged"""
        self.client.post(
            f'/admin/booking/{self.booking.id}/update-status/',
            {'status': 'confirmed'}
        )
        
        log = AdminActivityLog.objects.filter(
            admin_user=self.admin_user,
            action='update',
            module='bookings'
        ).first()
        self.assertIsNotNone(log)
    
    def test_booking_update_status_invalid_status(self):
        """Test updating booking with invalid status"""
        response = self.client.post(
            f'/admin/booking/{self.booking.id}/update-status/',
            {'status': 'invalid_status'}
        )
        
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, 'pending')


class AdminPaymentUpdateViewTest(TestCase):
    """Test payment update status view"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
        
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        user = DjangoUser.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='pass123'
        )
        
        coach_user = DjangoUser.objects.create_user(
            username='coach',
            email='coach@test.com',
            password='pass123'
        )
        coach = CoachProfile.objects.create(user=coach_user)
        
        category = Category.objects.create(name='Fitness')
        course = Course.objects.create(
            title='Test Course',
            coach=coach,
            price=100000,
            duration=60
        )
        
        booking = Booking.objects.create(
            user=user,
            coach=coach,
            course=course,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
            status='pending'
        )
        
        self.payment = Payment.objects.create(
            booking=booking,
            user=user,
            amount=100000,
            order_id='test-payment-order',
            status='pending'
        )
    
    def test_payment_update_status_pending_to_settlement(self):
        """Test updating payment status to settlement"""
        response = self.client.post(
            f'/admin/payment/{self.payment.id}/update-status/',
            {'status': 'settlement'}
        )
        
        self.assertEqual(response.status_code, 302)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'settlement')
    
    def test_payment_update_status_logs_activity(self):
        """Test payment status update is logged"""
        self.client.post(
            f'/admin/payment/{self.payment.id}/update-status/',
            {'status': 'settlement'}
        )
        
        log = AdminActivityLog.objects.filter(
            admin_user=self.admin_user,
            action='update',
            module='payments'
        ).first()
        self.assertIsNotNone(log)


class AdminDecoratorTest(TestCase):
    """Test admin_login_required decorator"""
    
    def setUp(self):
        self.client = Client()
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.admin_user.set_password('adminpass123')
        self.admin_user.save()
    
    def test_decorator_redirects_unauthenticated_user(self):
        """Test decorator redirects unauthenticated users"""
        response = self.client.get('/admin/users/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.endswith('/admin/login/'))
    
    def test_decorator_removes_invalid_session(self):
        """Test decorator removes invalid session"""
        session = self.client.session
        session['admin_user_id'] = 99999
        session.save()
        
        response = self.client.get('/admin/users/')
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('admin_user_id', self.client.session)
    
    def test_decorator_allows_authenticated_user(self):
        """Test decorator allows authenticated users"""
        self.client.post('/admin/login/', {
            'username': 'admin',
            'password': 'adminpass123'
        })
        
        response = self.client.get('/admin/users/')
        self.assertEqual(response.status_code, 200)


class LogAdminActivityHelperTest(TestCase):
    """Test log_admin_activity helper function"""
    
    def setUp(self):
        self.admin_user = AdminUser.objects.create(
            username='admin',
            email='admin@test.com'
        )
        self.factory = RequestFactory()
    
    def test_log_admin_activity_without_request(self):
        """Test logging activity without request"""
        from admin_panel.views import log_admin_activity
        
        log_admin_activity(
            self.admin_user,
            'login',
            'auth',
            'Test login'
        )
        
        log = AdminActivityLog.objects.get(admin_user=self.admin_user)
        self.assertEqual(log.action, 'login')
        self.assertIsNone(log.ip_address)
    
    def test_log_admin_activity_with_request(self):
        """Test logging activity with request"""
        from admin_panel.views import log_admin_activity
        
        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '192.168.1.1'
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0'
        
        log_admin_activity(
            self.admin_user,
            'view',
            'dashboard',
            'Test view',
            request
        )
        
        log = AdminActivityLog.objects.filter(admin_user=self.admin_user).first()
        self.assertIsNotNone(log)
    
    def test_log_admin_activity_with_x_forwarded_for(self):
        """Test logging activity with X-Forwarded-For header"""
        from admin_panel.views import log_admin_activity
        
        request = self.factory.get('/')
        request.META['HTTP_X_FORWARDED_FOR'] = '10.0.0.1, 192.168.1.1'
        
        log_admin_activity(
            self.admin_user,
            'view',
            'users',
            'Test',
            request
        )
        
        log = AdminActivityLog.objects.filter(admin_user=self.admin_user).first()
        self.assertIsNotNone(log)
