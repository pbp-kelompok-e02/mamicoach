from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from courses_and_coach.models import Course, Category
from user_profile.models import CoachProfile, UserProfile
from reviews.models import Review
from booking.models import Booking


class MainViewTest(TestCase):
    """Test cases for main view (landing page)"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()
        
        # Create coach user
        self.coach_user = User.objects.create_user(
            username='topcoach',
            email='coach@test.com',
            password='testpass123',
            first_name='Top',
            last_name='Coach'
        )
        self.coach = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Top rated coach',
            rating=4.8,
            verified=True
        )
        
        # Create another coach (unverified)
        self.unverified_coach_user = User.objects.create_user(
            username='unverifiedcoach',
            email='unverified@test.com',
            password='testpass123'
        )
        self.unverified_coach = CoachProfile.objects.create(
            user=self.unverified_coach_user,
            bio='Unverified coach',
            verified=False
        )
        
        # Create user for reviews
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123'
        )
        UserProfile.objects.create(user=self.user)
        
        # Create category
        self.category = Category.objects.create(
            name='Fitness',
            description='Fitness coaching'
        )
        
        # Create courses
        self.course1 = Course.objects.create(
            title='Top Course',
            coach=self.coach,
            category=self.category,
            price=100000,
            duration=60,
            description='High quality course'
        )
        
        self.course2 = Course.objects.create(
            title='Another Course',
            coach=self.unverified_coach,
            category=self.category,
            price=50000,
            duration=45,
            description='Good course'
        )
    
    def test_main_view_get(self):
        """Test main view can be accessed"""
        response = self.client.get(reverse('main:show_main'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/landing_page/index.html')
    
    def test_main_view_context_featured_courses(self):
        """Test featured courses are in context"""
        response = self.client.get(reverse('main:show_main'))
        self.assertIn('featured_courses', response.context)
        self.assertGreater(len(response.context['featured_courses']), 0)
    
    def test_main_view_context_categories(self):
        """Test categories are in context"""
        response = self.client.get(reverse('main:show_main'))
        self.assertIn('categories', response.context)
        self.assertGreater(len(response.context['categories']), 0)
    
    def test_main_view_context_top_coaches(self):
        """Test top coaches are in context (only verified)"""
        response = self.client.get(reverse('main:show_main'))
        self.assertIn('top_coaches', response.context)
        # Should only have verified coaches
        for coach in response.context['top_coaches']:
            self.assertTrue(coach.verified)
    
    def test_main_view_context_reviews(self):
        """Test reviews are in context"""
        response = self.client.get(reverse('main:show_main'))
        self.assertIn('top_reviews', response.context)
    
    def test_featured_courses_limit(self):
        """Test that only 4 featured courses are shown"""
        # Create more courses
        for i in range(5):
            Course.objects.create(
                title=f'Extra Course {i}',
                coach=self.coach,
                category=self.category,
                price=100000,
                duration=60
            )
        
        response = self.client.get(reverse('main:show_main'))
        # Should have max 4 featured courses
        self.assertLessEqual(len(response.context['featured_courses']), 4)
    
    def test_top_coaches_limit(self):
        """Test that only 6 top coaches are shown"""
        # Create more coaches
        for i in range(8):
            user = User.objects.create_user(
                username=f'coach{i}',
                password='testpass123'
            )
            CoachProfile.objects.create(
                user=user,
                rating=4.5 - (i * 0.1),
                verified=True
            )
        
        response = self.client.get(reverse('main:show_main'))
        # Should have max 6 top coaches
        self.assertLessEqual(len(response.context['top_coaches']), 6)
    
    def test_top_reviews_limit(self):
        """Test that only 10 top reviews are shown"""
        # Create bookings and reviews
        for i in range(12):
            Booking.objects.create(
                user=self.user,
                coach=self.coach,
                course=self.course1,
                start_datetime=timezone.now() + timedelta(days=i),
                end_datetime=timezone.now() + timedelta(days=i, hours=1),
                status='done'
            )
            Review.objects.create(
                user=self.user,
                course=self.course1,
                coach=self.coach,
                rating=5,
                comment=f'Great course {i}'
            )
        
        response = self.client.get(reverse('main:show_main'))
        # Should have max 10 top reviews
        self.assertLessEqual(len(response.context['top_reviews']), 10)
    
    def test_courses_ordered_by_coach_rating(self):
        """Test featured courses are ordered by coach rating"""
        # Create coach with higher rating
        high_rated_coach_user = User.objects.create_user(
            username='highrated',
            password='testpass123'
        )
        high_rated_coach = CoachProfile.objects.create(
            user=high_rated_coach_user,
            rating=5.0
        )
        
        high_rated_course = Course.objects.create(
            title='High Rated Course',
            coach=high_rated_coach,
            category=self.category,
            price=100000,
            duration=60
        )
        
        response = self.client.get(reverse('main:show_main'))
        featured = response.context['featured_courses']
        
        if len(featured) > 1:
            # Check that courses are ordered (first should have higher rating than last)
            self.assertGreaterEqual(
                featured[0].coach.rating,
                featured[-1].coach.rating
            )
    
    def test_reviews_ordered_by_rating_and_date(self):
        """Test reviews are ordered by rating (descending) then date"""
        # Create reviews with different ratings
        booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course1,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
            status='done'
        )
        
        review1 = Review.objects.create(
            user=self.user,
            course=self.course1,
            coach=self.coach,
            rating=3,
            comment='OK course'
        )
        
        review2 = Review.objects.create(
            user=self.user,
            course=self.course1,
            coach=self.coach,
            rating=5,
            comment='Excellent course'
        )
        
        response = self.client.get(reverse('main:show_main'))
        reviews = response.context['top_reviews']
        
        if len(reviews) >= 2:
            # Higher rated review should come first
            self.assertGreaterEqual(reviews[0].rating, reviews[-1].rating)
    
    def test_main_view_empty_data(self):
        """Test main view works with no data"""
        # Delete all data
        Course.objects.all().delete()
        CoachProfile.objects.all().delete()
        Review.objects.all().delete()
        Category.objects.all().delete()
        
        response = self.client.get(reverse('main:show_main'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['featured_courses']), 0)
        self.assertEqual(len(response.context['top_coaches']), 0)
        self.assertEqual(len(response.context['top_reviews']), 0)


class MainViewContextTest(TestCase):
    """Test context variables in main view"""
    
    def test_context_has_all_required_keys(self):
        """Test that context has all required keys"""
        client = Client()
        response = client.get(reverse('main:show_main'))
        
        required_keys = [
            'featured_courses',
            'categories',
            'top_coaches',
            'top_reviews'
        ]
        
        for key in required_keys:
            self.assertIn(key, response.context)
    
    def test_context_data_types(self):
        """Test context data types are correct"""
        client = Client()
        response = client.get(reverse('main:show_main'))
        
        # Can be QuerySet or list
        self.assertTrue(
            hasattr(response.context['featured_courses'], '__iter__'),
            "featured_courses should be iterable"
        )
        self.assertTrue(
            hasattr(response.context['categories'], '__iter__'),
            "categories should be iterable"
        )
        self.assertTrue(
            hasattr(response.context['top_coaches'], '__iter__'),
            "top_coaches should be iterable"
        )
        self.assertTrue(
            hasattr(response.context['top_reviews'], '__iter__'),
            "top_reviews should be iterable"
        )


class Error404ViewTest(TestCase):
    """Test 404 error handler"""
    
    def test_404_handler(self):
        """Test 404 error page"""
        client = Client()
        response = client.get('/nonexistent-page/')
        # Django will handle the 404 appropriately
        self.assertIn(response.status_code, [404, 301, 302])


class Error500ViewTest(TestCase):
    """Test 500 error handler"""
    
    def test_500_handler_view_exists(self):
        """Test 500 error view exists"""
        # This is a basic test to ensure the handler is defined
        from django.test.utils import override_settings
        from main.views import handler_500
        
        request = None
        # Handler just needs to be callable
        self.assertTrue(callable(handler_500))

