from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta

from reviews.models import Review
from reviews.forms import ReviewForm
from booking.models import Booking
from courses_and_coach.models import Course, Category
from user_profile.models import CoachProfile, UserProfile


class ReviewModelTestCase(TestCase):
    """Test cases for Review model"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.user = User.objects.create_user(username='student', password='pass123')
        self.coach_user = User.objects.create_user(username='coach', password='pass123')
        
        # Create user profiles
        UserProfile.objects.create(user=self.user)
        UserProfile.objects.create(user=self.coach_user)
        
        # Create coach profile
        self.coach = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Experienced coach',
            rating=0.0,
            rating_count=0
        )
        
        # Create category
        self.category = Category.objects.create(
            name='Programming',
            description='Programming courses'
        )
        
        # Create course
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title='Python Basics',
            description='Learn Python',
            location='Online',
            price=100000,
            duration=60,
            rating=0.0,
            rating_count=0
        )
        
        # Create booking
        self.booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
            status='done'
        )
    
    def test_review_creation(self):
        """Test review creation with valid data"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='Excellent course! Very informative.',
            is_anonymous=False
        )
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.course, self.course)
        self.assertFalse(review.is_anonymous)
        self.assertEqual(str(review), f"Review by {self.user.username} for {self.course.title}")
    
    def test_review_creation_anonymous(self):
        """Test anonymous review creation"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=4,
            content='Good course',
            is_anonymous=True
        )
        self.assertTrue(review.is_anonymous)
    
    def test_review_timestamps(self):
        """Test review created_at and updated_at timestamps"""
        before = timezone.now()
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=3,
            content='Average course'
        )
        after = timezone.now()
        
        self.assertGreaterEqual(review.created_at, before)
        self.assertLessEqual(review.created_at, after)
        self.assertGreaterEqual(review.updated_at, before)
        self.assertLessEqual(review.updated_at, after)
    
    def test_review_rating_range(self):
        """Test review with different rating values"""
        for rating in [1, 2, 3, 4, 5]:
            booking = Booking.objects.create(
                user=self.user,
                coach=self.coach,
                course=self.course,
                start_datetime=timezone.now() + timedelta(days=rating),
                end_datetime=timezone.now() + timedelta(days=rating, hours=1),
                status='done'
            )
            review = Review.objects.create(
                course=self.course,
                booking=booking,
                user=self.user,
                coach=self.coach,
                rating=rating,
                content=f'Rating {rating}'
            )
            self.assertEqual(review.rating, rating)
    
    def test_update_ratings_single_review(self):
        """Test that course and coach ratings update after review creation"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='Excellent course!'
        )
        
        # Refresh course and coach from database
        self.course.refresh_from_db()
        self.coach.refresh_from_db()
        
        self.assertEqual(self.course.rating, 5.0)
        self.assertEqual(self.course.rating_count, 1)
        self.assertEqual(self.coach.rating, 5.0)
        self.assertEqual(self.coach.rating_count, 1)
    
    def test_update_ratings_multiple_reviews(self):
        """Test that ratings are averaged correctly with multiple reviews"""
        # Create multiple bookings and reviews
        bookings = []
        ratings = [5, 4, 3]
        
        for i, rating in enumerate(ratings):
            booking = Booking.objects.create(
                user=self.user,
                coach=self.coach,
                course=self.course,
                start_datetime=timezone.now() + timedelta(days=i+2),
                end_datetime=timezone.now() + timedelta(days=i+2, hours=1),
                status='done'
            )
            bookings.append(booking)
            
            Review.objects.create(
                course=self.course,
                booking=booking,
                user=self.user,
                coach=self.coach,
                rating=rating,
                content=f'Review with rating {rating}'
            )
        
        # Check averages
        self.course.refresh_from_db()
        self.coach.refresh_from_db()
        
        expected_avg = sum(ratings) / len(ratings)  # 4.0
        self.assertEqual(self.course.rating, expected_avg)
        self.assertEqual(self.course.rating_count, 3)
        self.assertEqual(self.coach.rating, expected_avg)
        self.assertEqual(self.coach.rating_count, 3)
    
    def test_update_ratings_after_review_edit(self):
        """Test that ratings update when a review is edited"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=3,
            content='Average'
        )
        
        # Edit review
        review.rating = 5
        review.content = 'Actually excellent!'
        review.save()
        
        self.course.refresh_from_db()
        self.coach.refresh_from_db()
        
        self.assertEqual(self.course.rating, 5.0)
        self.assertEqual(self.coach.rating, 5.0)
    
    def test_review_one_to_one_booking(self):
        """Test that only one review can exist per booking"""
        Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='First review'
        )
        
        # Attempt to create another review for same booking should fail
        with self.assertRaises(Exception):
            Review.objects.create(
                course=self.course,
                booking=self.booking,
                user=self.user,
                coach=self.coach,
                rating=4,
                content='Second review'
            )


class ReviewFormTestCase(TestCase):
    """Test cases for ReviewForm"""
    
    def test_form_valid_data(self):
        """Test form with valid data"""
        form = ReviewForm(data={
            'rating': 5,
            'content': 'This is a great course with excellent content.',
            'is_anonymous': False
        })
        self.assertTrue(form.is_valid())
    
    def test_form_missing_rating(self):
        """Test form validation when rating is missing"""
        form = ReviewForm(data={
            'rating': '',
            'content': 'Good course',
            'is_anonymous': False
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)
    
    def test_form_invalid_rating_too_low(self):
        """Test form validation when rating is below minimum"""
        form = ReviewForm(data={
            'rating': 0,
            'content': 'Good course',
            'is_anonymous': False
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)
    
    def test_form_invalid_rating_too_high(self):
        """Test form validation when rating is above maximum"""
        form = ReviewForm(data={
            'rating': 6,
            'content': 'Good course',
            'is_anonymous': False
        })
        self.assertFalse(form.is_valid())
        self.assertIn('rating', form.errors)
    
    def test_form_missing_content(self):
        """Test form validation when content is missing"""
        form = ReviewForm(data={
            'rating': 5,
            'content': '',
            'is_anonymous': False
        })
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_form_content_too_short(self):
        """Test form validation when content is too short"""
        form = ReviewForm(data={
            'rating': 5,
            'content': 'Short',
            'is_anonymous': False
        })
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_form_content_too_long(self):
        """Test form validation when content exceeds maximum"""
        long_content = 'a' * 5001
        form = ReviewForm(data={
            'rating': 5,
            'content': long_content,
            'is_anonymous': False
        })
        self.assertFalse(form.is_valid())
        self.assertIn('content', form.errors)
    
    def test_form_content_exactly_minimum(self):
        """Test form with content exactly at minimum length (10 chars)"""
        form = ReviewForm(data={
            'rating': 5,
            'content': '1234567890',
            'is_anonymous': False
        })
        self.assertTrue(form.is_valid())
    
    def test_form_content_exactly_maximum(self):
        """Test form with content exactly at maximum length (5000 chars)"""
        max_content = 'a' * 5000
        form = ReviewForm(data={
            'rating': 5,
            'content': max_content,
            'is_anonymous': False
        })
        self.assertTrue(form.is_valid())
    
    def test_form_content_whitespace_only(self):
        """Test form validation with whitespace-only content"""
        form = ReviewForm(data={
            'rating': 5,
            'content': '          ',
            'is_anonymous': False
        })
        self.assertFalse(form.is_valid())
    
    def test_form_anonymous_true(self):
        """Test form with anonymous posting enabled"""
        form = ReviewForm(data={
            'rating': 4,
            'content': 'This is an anonymous review here.',
            'is_anonymous': True
        })
        self.assertTrue(form.is_valid())
    
    def test_form_anonymous_false(self):
        """Test form with anonymous posting disabled"""
        form = ReviewForm(data={
            'rating': 4,
            'content': 'This is a named review.',
            'is_anonymous': False
        })
        self.assertTrue(form.is_valid())
    
    def test_form_all_rating_values(self):
        """Test form with all valid rating values"""
        for rating in range(1, 6):
            form = ReviewForm(data={
                'rating': rating,
                'content': 'Valid review content here',
                'is_anonymous': False
            })
            self.assertTrue(form.is_valid(), f"Form should be valid for rating {rating}")


class ReviewViewTestCase(TestCase):
    """Test cases for Review views"""
    
    def setUp(self):
        """Set up test data and client"""
        self.client = Client()
        
        # Create users
        self.user = User.objects.create_user(username='student', password='pass123')
        self.other_user = User.objects.create_user(username='other_student', password='pass123')
        self.coach_user = User.objects.create_user(username='coach', password='pass123')
        
        # Create user profiles
        UserProfile.objects.create(user=self.user)
        UserProfile.objects.create(user=self.other_user)
        UserProfile.objects.create(user=self.coach_user)
        
        # Create coach profile
        self.coach = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Experienced coach',
            rating=0.0,
            rating_count=0
        )
        
        # Create category
        self.category = Category.objects.create(
            name='Programming',
            description='Programming courses'
        )
        
        # Create course
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title='Python Basics',
            description='Learn Python',
            location='Online',
            price=100000,
            duration=60,
            rating=0.0,
            rating_count=0
        )
        
        # Create booking
        self.booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
            status='done'
        )
    
    def test_create_review_not_logged_in(self):
        """Test that non-logged-in user is redirected to login"""
        response = self.client.get(
            reverse('reviews:create_review', args=[self.booking.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)
    
    def test_create_review_get_form(self):
        """Test GET request to create review shows form"""
        self.client.login(username='student', password='pass123')
        response = self.client.get(
            reverse('reviews:create_review', args=[self.booking.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertFalse(response.context['is_edit'])
    
    def test_create_review_invalid_booking(self):
        """Test creating review for non-existent booking"""
        self.client.login(username='student', password='pass123')
        response = self.client.get(
            reverse('reviews:create_review', args=[9999])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main:show_main'))
    
    def test_create_review_permission_denied(self):
        """Test that user cannot create review for other user's booking"""
        self.client.login(username='other_student', password='pass123')
        response = self.client.get(
            reverse('reviews:create_review', args=[self.booking.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main:show_main'))
    
    def test_create_review_post_valid(self):
        """Test successfully creating a review with POST"""
        self.client.login(username='student', password='pass123')
        response = self.client.post(
            reverse('reviews:create_review', args=[self.booking.id]),
            data={
                'rating': 5,
                'content': 'Excellent course experience!',
                'is_anonymous': False
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Review.objects.filter(booking=self.booking).exists())
        
        review = Review.objects.get(booking=self.booking)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.content, 'Excellent course experience!')
        self.assertFalse(review.is_anonymous)
    
    def test_create_review_post_with_next_parameter(self):
        """Test that callback URL is used when provided"""
        self.client.login(username='student', password='pass123')
        callback_url = '/dashboard'
        response = self.client.post(
            reverse('reviews:create_review', args=[self.booking.id]) + f'?next={callback_url}',
            data={
                'rating': 5,
                'content': 'Great course content.',
                'is_anonymous': False
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, callback_url)
    
    def test_create_review_already_exists(self):
        """Test that user cannot create review if one already exists"""
        # Create initial review
        Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='First review'
        )
        
        self.client.login(username='student', password='pass123')
        response = self.client.get(
            reverse('reviews:create_review', args=[self.booking.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main:show_main'))
    
    def test_create_review_post_invalid_form(self):
        """Test creating review with invalid form data"""
        self.client.login(username='student', password='pass123')
        response = self.client.post(
            reverse('reviews:create_review', args=[self.booking.id]),
            data={
                'rating': 6,  # Invalid: > 5
                'content': 'short',  # Invalid: < 10 chars
                'is_anonymous': False
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Review.objects.filter(booking=self.booking).exists())
    
    def test_edit_review_not_logged_in(self):
        """Test that non-logged-in user is redirected to login for edit"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='Initial review'
        )
        
        response = self.client.get(
            reverse('reviews:edit_review', args=[review.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)
    
    def test_edit_review_get_form(self):
        """Test GET request to edit review shows form with existing data"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=3,
            content='Initial review content'
        )
        
        self.client.login(username='student', password='pass123')
        response = self.client.get(
            reverse('reviews:edit_review', args=[review.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('form', response.context)
        self.assertTrue(response.context['is_edit'])
    
    def test_edit_review_invalid_review(self):
        """Test editing non-existent review"""
        self.client.login(username='student', password='pass123')
        response = self.client.get(
            reverse('reviews:edit_review', args=[9999])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main:show_main'))
    
    def test_edit_review_permission_denied(self):
        """Test that user cannot edit other user's review"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='User review'
        )
        
        self.client.login(username='other_student', password='pass123')
        response = self.client.get(
            reverse('reviews:edit_review', args=[review.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main:show_main'))
    
    def test_edit_review_post_valid(self):
        """Test successfully updating a review with POST"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=3,
            content='Initial review'
        )
        
        self.client.login(username='student', password='pass123')
        response = self.client.post(
            reverse('reviews:edit_review', args=[review.id]),
            data={
                'rating': 5,
                'content': 'Updated review with excellent feedback!',
                'is_anonymous': True
            }
        )
        
        self.assertEqual(response.status_code, 302)
        review.refresh_from_db()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.content, 'Updated review with excellent feedback!')
        self.assertTrue(review.is_anonymous)
    
    def test_edit_review_post_with_next_parameter(self):
        """Test that callback URL is used for edit redirect"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=3,
            content='Initial'
        )
        
        self.client.login(username='student', password='pass123')
        callback_url = '/my-reviews'
        response = self.client.post(
            reverse('reviews:edit_review', args=[review.id]) + f'?next={callback_url}',
            data={
                'rating': 5,
                'content': 'Updated review here.',
                'is_anonymous': False
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, callback_url)
    
    def test_edit_review_post_invalid_form(self):
        """Test editing review with invalid form data"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=3,
            content='Initial content'
        )
        
        self.client.login(username='student', password='pass123')
        response = self.client.post(
            reverse('reviews:edit_review', args=[review.id]),
            data={
                'rating': 0,  # Invalid
                'content': 'x',  # Invalid
                'is_anonymous': False
            }
        )
        
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.rating, 3)  # Should remain unchanged
    
    def test_delete_review_not_logged_in(self):
        """Test that non-logged-in user is redirected to login for delete"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='Review to delete'
        )
        
        response = self.client.post(
            reverse('reviews:delete_review', args=[review.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.url)
    
    def test_delete_review_invalid_review(self):
        """Test deleting non-existent review"""
        self.client.login(username='student', password='pass123')
        response = self.client.post(
            reverse('reviews:delete_review', args=[9999])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main:show_main'))
    
    def test_delete_review_permission_denied(self):
        """Test that user cannot delete other user's review"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='Review'
        )
        
        self.client.login(username='other_student', password='pass123')
        response = self.client.post(
            reverse('reviews:delete_review', args=[review.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main:show_main'))
    
    def test_delete_review_post_valid(self):
        """Test successfully deleting a review with POST"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='Review to delete'
        )
        
        review_id = review.id
        self.client.login(username='student', password='pass123')
        response = self.client.post(
            reverse('reviews:delete_review', args=[review_id])
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(id=review_id).exists())
    
    def test_delete_review_post_with_next_parameter(self):
        """Test that callback URL is used for delete redirect"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='Review'
        )
        
        self.client.login(username='student', password='pass123')
        callback_url = '/my-reviews'
        response = self.client.post(
            reverse('reviews:delete_review', args=[review.id]) + f'?next={callback_url}'
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, callback_url)
    
    def test_delete_review_get_invalid_method(self):
        """Test that GET request to delete review returns error"""
        review = Review.objects.create(
            course=self.course,
            booking=self.booking,
            user=self.user,
            coach=self.coach,
            rating=5,
            content='Review'
        )
        
        self.client.login(username='student', password='pass123')
        response = self.client.get(
            reverse('reviews:delete_review', args=[review.id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('main:show_main'))
        # Review should still exist
        self.assertTrue(Review.objects.filter(id=review.id).exists())


class ReviewIntegrationTestCase(TestCase):
    """Integration tests for review workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        self.user = User.objects.create_user(username='student', password='pass123')
        self.coach_user = User.objects.create_user(username='coach', password='pass123')
        
        UserProfile.objects.create(user=self.user)
        UserProfile.objects.create(user=self.coach_user)
        
        self.coach = CoachProfile.objects.create(
            user=self.coach_user,
            bio='Coach',
            rating=0.0,
            rating_count=0
        )
        
        self.category = Category.objects.create(name='Tech')
        
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title='Course',
            description='Desc',
            price=100000,
            duration=60,
            rating=0.0,
            rating_count=0
        )
        
        self.booking = Booking.objects.create(
            user=self.user,
            coach=self.coach,
            course=self.course,
            start_datetime=timezone.now() + timedelta(days=1),
            end_datetime=timezone.now() + timedelta(days=1, hours=1),
            status='done'
        )
    
    def test_full_review_lifecycle_create_edit_delete(self):
        """Test complete review lifecycle: create, edit, delete"""
        self.client.login(username='student', password='pass123')
        
        # Create review
        self.client.post(
            reverse('reviews:create_review', args=[self.booking.id]),
            data={
                'rating': 4,
                'content': 'Good course overall.',
                'is_anonymous': False
            }
        )
        
        review = Review.objects.get(booking=self.booking)
        initial_id = review.id
        self.assertEqual(review.rating, 4)
        
        # Edit review
        self.client.post(
            reverse('reviews:edit_review', args=[review.id]),
            data={
                'rating': 5,
                'content': 'Actually excellent course!',
                'is_anonymous': False
            }
        )
        
        review.refresh_from_db()
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.content, 'Actually excellent course!')
        
        # Delete review
        self.client.post(
            reverse('reviews:delete_review', args=[review.id])
        )
        
        self.assertFalse(Review.objects.filter(id=initial_id).exists())
    
    def test_multiple_reviews_rating_calculation(self):
        """Test that multiple reviews calculate ratings correctly"""
        self.client.login(username='student', password='pass123')
        
        # Create multiple reviews
        ratings = [5, 4, 3, 5, 4]
        for i, rating in enumerate(ratings):
            booking = Booking.objects.create(
                user=self.user,
                coach=self.coach,
                course=self.course,
                start_datetime=timezone.now() + timedelta(days=i+2),
                end_datetime=timezone.now() + timedelta(days=i+2, hours=1),
                status='done'
            )
            
            self.client.post(
                reverse('reviews:create_review', args=[booking.id]),
                data={
                    'rating': rating,
                    'content': f'Review with {rating} stars.',
                    'is_anonymous': False
                }
            )
        
        self.course.refresh_from_db()
        self.coach.refresh_from_db()
        
        expected_avg = sum(ratings) / len(ratings)
        self.assertEqual(self.course.rating, expected_avg)
        self.assertEqual(self.coach.rating, expected_avg)
        self.assertEqual(self.course.rating_count, len(ratings))
        self.assertEqual(self.coach.rating_count, len(ratings))
