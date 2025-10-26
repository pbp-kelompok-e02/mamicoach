from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Course, Category
from user_profile.models import CoachProfile
from .forms import CourseForm


class CategoryModelTest(TestCase):
    """Test cases for Category model"""

    def setUp(self):
        self.category = Category.objects.create(
            name="Yoga",
            description="Yoga classes for all levels",
            thumbnail_url="https://example.com/yoga.jpg",
        )

    def test_category_creation(self):
        """Test category can be created"""
        self.assertEqual(self.category.name, "Yoga")
        self.assertEqual(self.category.description, "Yoga classes for all levels")
        self.assertIsNotNone(self.category.id)

    def test_category_str(self):
        """Test category string representation"""
        self.assertEqual(str(self.category), "Yoga")

    def test_category_ordering(self):
        """Test categories are ordered by name"""
        Category.objects.create(name="Fitness")
        Category.objects.create(name="Aerobic")
        categories = Category.objects.all()
        self.assertEqual(categories[0].name, "Aerobic")
        self.assertEqual(categories[1].name, "Fitness")
        self.assertEqual(categories[2].name, "Yoga")

    def test_get_url_name(self):
        """Test URL-safe name generation"""
        category = Category.objects.create(name="Martial Arts")
        self.assertEqual(category.get_url_name(), "Martial%20Arts")


class CourseModelTest(TestCase):
    """Test cases for Course model"""

    def setUp(self):
        # Create user and coach profile
        self.user = User.objects.create_user(
            username="testcoach",
            password="testpass123",
            first_name="Test",
            last_name="Coach",
        )
        self.coach = CoachProfile.objects.create(
            user=self.user,
            bio="Experienced coach",
            expertise=["Yoga", "Fitness"],
            rating=4.5,
            verified=True,
        )
        self.category = Category.objects.create(name="Yoga")

        # Create course
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title="Beginner Yoga",
            description="Perfect for beginners",
            location="Online",
            price=100000,
            duration=60,
            thumbnail_url="https://example.com/course.jpg",
        )

    def test_course_creation(self):
        """Test course can be created with all fields"""
        self.assertEqual(self.course.title, "Beginner Yoga")
        self.assertEqual(self.course.coach, self.coach)
        self.assertEqual(self.course.category, self.category)
        self.assertEqual(self.course.price, 100000)
        self.assertEqual(self.course.duration, 60)

    def test_course_str(self):
        """Test course string representation"""
        self.assertIn("Beginner Yoga", str(self.course))

    def test_course_default_values(self):
        """Test course default values"""
        self.assertEqual(self.course.rating, 0.0)
        self.assertEqual(self.course.rating_count, 0)
        self.assertEqual(self.course.location, "Online")

    def test_course_coach_relationship(self):
        """Test course-coach relationship"""
        self.assertEqual(self.coach.courses.count(), 1)
        self.assertEqual(self.coach.courses.first(), self.course)

    def test_course_category_deletion(self):
        """Test course category can be set to null on category deletion"""
        self.category.delete()
        self.course.refresh_from_db()
        self.assertIsNone(self.course.category)


class CourseFormTest(TestCase):
    """Test cases for CourseForm"""

    def setUp(self):
        self.category = Category.objects.create(name="Fitness")

    def test_valid_form(self):
        """Test form with valid data"""
        form_data = {
            "category": self.category.id,
            "title": "Advanced Fitness",
            "description": "High intensity training",
            "location": "Jakarta",
            "price": 150000,
            "duration": 90,
            "thumbnail_url": "https://example.com/fitness.jpg",
        }
        form = CourseForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_invalid_form_missing_required_fields(self):
        """Test form with missing required fields"""
        form = CourseForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("description", form.errors)
        self.assertIn("price", form.errors)

    def test_invalid_price(self):
        """Test form with negative price"""
        form_data = {
            "category": self.category.id,
            "title": "Test Course",
            "description": "Description",
            "location": "Online",
            "price": -1000,
            "duration": 60,
        }
        form = CourseForm(data=form_data)
        self.assertFalse(form.is_valid())


class CourseViewsTest(TestCase):
    """Test cases for course views"""

    def setUp(self):
        self.client = Client()

        # Create users
        self.user = User.objects.create_user(
            username="testuser", password="testpass123"
        )
        self.coach_user = User.objects.create_user(
            username="testcoach", password="testpass123"
        )

        # Create coach profile
        self.coach = CoachProfile.objects.create(
            user=self.coach_user, bio="Test coach", expertise=["Yoga"], verified=True
        )

        # Create category and courses
        self.category = Category.objects.create(name="Yoga")
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title="Test Course",
            description="Test description",
            price=100000,
            duration=60,
        )

    def test_show_courses_view(self):
        """Test courses list view"""
        response = self.client.get(reverse("courses_and_coach:show_courses"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")
        self.assertTemplateUsed(response, "courses_and_coach/courses_list.html")

    def test_show_courses_pagination(self):
        """Test courses list pagination"""
        response = self.client.get(
            reverse("courses_and_coach:show_courses") + "?page=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("courses", response.context)
        self.assertIn("current_page", response.context)
        self.assertIn("total_pages", response.context)

    def test_show_courses_search(self):
        """Test courses search functionality"""
        response = self.client.get(
            reverse("courses_and_coach:show_courses") + "?search=Test"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")

    def test_show_courses_category_filter(self):
        """Test courses category filter"""
        response = self.client.get(
            reverse("courses_and_coach:show_courses") + "?category=Yoga"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")

    def test_course_details_view(self):
        """Test course details view"""
        response = self.client.get(
            reverse("courses_and_coach:course_details", args=[self.course.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")
        self.assertContains(response, "Test description")
        self.assertTemplateUsed(
            response, "courses_and_coach/courses/courses_details.html"
        )

    def test_course_details_not_found(self):
        """Test course details with invalid ID"""
        response = self.client.get(
            reverse("courses_and_coach:course_details", args=[99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_create_course_requires_login(self):
        """Test create course requires authentication"""
        response = self.client.get(reverse("courses_and_coach:create_course"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_create_course_requires_coach_profile(self):
        """Test create course requires coach profile"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("courses_and_coach:create_course"))
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_create_course_with_coach(self):
        """Test create course with coach profile"""
        self.client.login(username="testcoach", password="testpass123")
        response = self.client.get(reverse("courses_and_coach:create_course"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, "courses_and_coach/courses/create_course.html"
        )

    def test_create_course_post(self):
        """Test creating a course via POST"""
        self.client.login(username="testcoach", password="testpass123")
        form_data = {
            "category": self.category.id,
            "title": "New Course",
            "description": "New description",
            "location": "Online",
            "price": 200000,
            "duration": 90,
        }
        response = self.client.post(
            reverse("courses_and_coach:create_course"), data=form_data
        )
        self.assertEqual(Course.objects.filter(title="New Course").count(), 1)
        self.assertEqual(response.status_code, 302)  # Redirect after creation

    def test_my_courses_view(self):
        """Test my courses view"""
        self.client.login(username="testcoach", password="testpass123")
        response = self.client.get(reverse("courses_and_coach:my_courses"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")
        self.assertTemplateUsed(response, "courses_and_coach/courses/my_courses.html")

    def test_edit_course_view(self):
        """Test edit course view"""
        self.client.login(username="testcoach", password="testpass123")
        response = self.client.get(
            reverse("courses_and_coach:edit_course", args=[self.course.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses_and_coach/courses/edit_course.html")

    def test_edit_course_unauthorized(self):
        """Test edit course by non-owner"""
        other_user = User.objects.create_user(username="other", password="pass")
        CoachProfile.objects.create(user=other_user, bio="Other coach")
        self.client.login(username="other", password="pass")
        response = self.client.get(
            reverse("courses_and_coach:edit_course", args=[self.course.id])
        )
        self.assertEqual(response.status_code, 302)  # Redirect

    def test_delete_course_view(self):
        """Test delete course view"""
        self.client.login(username="testcoach", password="testpass123")
        response = self.client.post(
            reverse("courses_and_coach:delete_course", args=[self.course.id])
        )
        self.assertEqual(Course.objects.filter(id=self.course.id).count(), 0)
        self.assertEqual(response.status_code, 302)  # Redirect after deletion

    def test_category_detail_view(self):
        """Test category detail view"""
        response = self.client.get(
            reverse("courses_and_coach:category_detail", args=["Yoga"])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Course")
        self.assertTemplateUsed(response, "courses_and_coach/category_detail.html")


class CoachViewsTest(TestCase):
    """Test cases for coach views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="testcoach",
            password="testpass123",
            first_name="Test",
            last_name="Coach",
        )
        self.coach = CoachProfile.objects.create(
            user=self.user,
            bio="Expert coach",
            expertise=["Yoga", "Fitness"],
            rating=4.5,
            verified=True,
        )

    def test_show_coaches_view(self):
        """Test coaches list view"""
        response = self.client.get(reverse("courses_and_coach:show_coaches"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Coach")
        self.assertTemplateUsed(response, "courses_and_coach/coaches_list.html")

    def test_show_coaches_pagination(self):
        """Test coaches list pagination"""
        response = self.client.get(
            reverse("courses_and_coach:show_coaches") + "?page=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("coaches", response.context)
        self.assertIn("current_page", response.context)
        self.assertIn("total_pages", response.context)

    def test_coach_details_view(self):
        """Test coach details view"""
        response = self.client.get(
            reverse("courses_and_coach:coach_details", args=[self.coach.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Coach")
        self.assertContains(response, "Expert coach")
        self.assertTemplateUsed(
            response, "courses_and_coach/coaches/coach_details.html"
        )

    def test_coach_details_not_found(self):
        """Test coach details with invalid ID"""
        response = self.client.get(
            reverse("courses_and_coach:coach_details", args=[99999])
        )
        self.assertEqual(response.status_code, 404)


class AjaxViewsTest(TestCase):
    """Test cases for AJAX views"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="coach", password="pass")
        self.coach = CoachProfile.objects.create(user=self.user, bio="Test")
        self.category = Category.objects.create(name="Yoga")
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title="AJAX Test Course",
            description="Test",
            price=100000,
            duration=60,
        )

    def test_courses_ajax_view(self):
        """Test courses AJAX endpoint"""
        response = self.client.get(reverse("courses_and_coach:courses_ajax"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertIn("courses", data)

    def test_courses_card_ajax_view(self):
        """Test courses card AJAX endpoint"""
        response = self.client.get(reverse("courses_and_coach:courses_card_ajax"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        data = response.json()
        self.assertIn("html", data)
        self.assertIn("total_count", data)
        self.assertIn("count", data)

    def test_courses_by_id_ajax_view(self):
        """Test courses by ID AJAX endpoint"""
        response = self.client.get(
            reverse("courses_and_coach:courses_by_id_ajax", args=[self.course.id])
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("course", data)
        self.assertEqual(data["course"]["title"], "AJAX Test Course")

    def test_courses_ajax_with_search(self):
        """Test AJAX search functionality"""
        response = self.client.get(
            reverse("courses_and_coach:courses_ajax") + "?search=AJAX"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["courses"]), 1)

    def test_courses_ajax_with_category_filter(self):
        """Test AJAX category filter"""
        response = self.client.get(
            reverse("courses_and_coach:courses_ajax") + "?category=Yoga"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["courses"]), 1)

    def test_course_duration_formatted_hours_only(self):
        """Test duration_formatted with hours only (no minutes)"""
        course = Course.objects.create(
            coach=self.coach,
            title="Test Course",
            description="Test",
            price=100000,
            duration=120  # 2 hours
        )
        self.assertEqual(course.duration_formatted, "2h")
    
    def test_course_duration_formatted_hours_and_minutes(self):
        """Test duration_formatted with hours and minutes"""
        course = Course.objects.create(
            coach=self.coach,
            title="Test Course",
            description="Test",
            price=100000,
            duration=90  # 1 hour 30 minutes
        )
        self.assertEqual(course.duration_formatted, "1h 30m")


class MyCourseViewTest(TestCase):
    """Test cases for my_courses view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testcoach',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.user, bio='Test')
        self.category = Category.objects.create(name='Test')
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title='My Course',
            description='Test',
            price=100000,
            duration=60
        )
    
    def test_my_courses_requires_login(self):
        """Test my courses requires authentication"""
        response = self.client.get(reverse('courses_and_coach:my_courses'))
        self.assertEqual(response.status_code, 302)
    
    def test_my_courses_requires_coach_profile(self):
        """Test my courses requires coach profile"""
        regular_user = User.objects.create_user(
            username='regularuser',
            password='testpass123'
        )
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(reverse('courses_and_coach:my_courses'))
        self.assertEqual(response.status_code, 302)
    
    def test_my_courses_coach_view(self):
        """Test my courses view for coach"""
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.get(reverse('courses_and_coach:my_courses'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Course')
    
    def test_my_courses_empty(self):
        """Test my courses with no courses"""
        self.course.delete()
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.get(reverse('courses_and_coach:my_courses'))
        self.assertEqual(response.status_code, 200)


class EditCourseViewTest(TestCase):
    """Test cases for edit_course view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testcoach',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.user, bio='Test')
        self.category = Category.objects.create(name='Test')
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title='Test Course',
            description='Test',
            price=100000,
            duration=60
        )
    
    def test_edit_course_requires_login(self):
        """Test edit course requires authentication"""
        response = self.client.get(
            reverse('courses_and_coach:edit_course', args=[self.course.id])
        )
        self.assertEqual(response.status_code, 302)
    
    def test_edit_course_requires_coach_profile(self):
        """Test edit course requires coach profile"""
        regular_user = User.objects.create_user(
            username='regularuser',
            password='testpass123'
        )
        self.client.login(username='regularuser', password='testpass123')
        response = self.client.get(
            reverse('courses_and_coach:edit_course', args=[self.course.id])
        )
        self.assertEqual(response.status_code, 302)
    
    def test_edit_course_owner_only(self):
        """Test edit course only by owner"""
        other_coach_user = User.objects.create_user(
            username='othercoach',
            password='testpass123'
        )
        CoachProfile.objects.create(user=other_coach_user)
        self.client.login(username='othercoach', password='testpass123')
        response = self.client.get(
            reverse('courses_and_coach:edit_course', args=[self.course.id])
        )
        self.assertEqual(response.status_code, 302)
    
    def test_edit_course_get(self):
        """Test edit course GET request"""
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.get(
            reverse('courses_and_coach:edit_course', args=[self.course.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'courses_and_coach/courses/edit_course.html')
    
    def test_edit_course_post_success(self):
        """Test edit course POST success"""
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.post(
            reverse('courses_and_coach:edit_course', args=[self.course.id]),
            {
                'category': self.category.id,
                'title': 'Updated Course',
                'description': 'Updated description',
                'location': 'Online',
                'price': 150000,
                'duration': 90
            }
        )
        self.assertEqual(response.status_code, 302)
        self.course.refresh_from_db()
        self.assertEqual(self.course.title, 'Updated Course')


class DeleteCourseViewTest(TestCase):
    """Test cases for delete_course view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testcoach',
            password='testpass123'
        )
        self.coach = CoachProfile.objects.create(user=self.user, bio='Test')
        self.category = Category.objects.create(name='Test')
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title='Test Course',
            description='Test',
            price=100000,
            duration=60
        )
    
    def test_delete_course_requires_login(self):
        """Test delete course requires authentication"""
        response = self.client.get(
            reverse('courses_and_coach:delete_course', args=[self.course.id])
        )
        self.assertEqual(response.status_code, 302)
    
    def test_delete_course_owner_only(self):
        """Test delete course only by owner"""
        other_coach_user = User.objects.create_user(
            username='othercoach',
            password='testpass123'
        )
        CoachProfile.objects.create(user=other_coach_user)
        self.client.login(username='othercoach', password='testpass123')
        response = self.client.post(
            reverse('courses_and_coach:delete_course', args=[self.course.id])
        )
        self.assertEqual(response.status_code, 302)
        # Course should still exist
        self.assertTrue(Course.objects.filter(id=self.course.id).exists())
    
    def test_delete_course_get(self):
        """Test delete course confirmation page"""
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.get(
            reverse('courses_and_coach:delete_course', args=[self.course.id])
        )
        self.assertEqual(response.status_code, 200)
    
    def test_delete_course_post(self):
        """Test delete course POST"""
        course_id = self.course.id
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.post(
            reverse('courses_and_coach:delete_course', args=[self.course.id])
        )
        self.assertEqual(response.status_code, 302)
        # Course should be deleted
        self.assertFalse(Course.objects.filter(id=course_id).exists())


class CategoryDetailViewTest(TestCase):
    """Test cases for category_detail view"""
    
    def setUp(self):
        self.client = Client()
        self.category = Category.objects.create(name='Yoga')
        
        self.user = User.objects.create_user(username='coach', password='pass')
        self.coach = CoachProfile.objects.create(
            user=self.user,
            bio='Test',
            expertise=['Yoga']
        )
        
        self.course = Course.objects.create(
            coach=self.coach,
            category=self.category,
            title='Yoga Course',
            description='Test',
            price=100000,
            duration=60
        )
    
    def test_category_detail_view(self):
        """Test category detail view"""
        response = self.client.get(
            reverse('courses_and_coach:category_detail', args=['Yoga'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Yoga Course')
    
    def test_category_detail_not_found(self):
        """Test category detail with invalid category"""
        response = self.client.get(
            reverse('courses_and_coach:category_detail', args=['NonExistent'])
        )
        self.assertEqual(response.status_code, 404)
    
    def test_category_detail_with_search(self):
        """Test category detail with search"""
        response = self.client.get(
            reverse('courses_and_coach:category_detail', args=['Yoga']) + '?search=Yoga'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Yoga Course')
    
    def test_category_detail_coaches_count(self):
        """Test category detail shows coach count"""
        response = self.client.get(
            reverse('courses_and_coach:category_detail', args=['Yoga'])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('coaches_count', response.context)


class ShowCoachesViewTest(TestCase):
    """Test cases for show_coaches view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='coach1',
            first_name='John',
            last_name='Doe',
            password='pass'
        )
        self.coach = CoachProfile.objects.create(
            user=self.user,
            bio='Expert coach',
            rating=4.5,
            verified=True
        )
    
    def test_show_coaches_view(self):
        """Test show coaches view"""
        response = self.client.get(reverse('courses_and_coach:show_coaches'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John')
    
    def test_show_coaches_search_by_name(self):
        """Test coaches search by name"""
        response = self.client.get(
            reverse('courses_and_coach:show_coaches') + '?search=John'
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John')
    
    def test_show_coaches_pagination(self):
        """Test coaches pagination"""
        response = self.client.get(
            reverse('courses_and_coach:show_coaches') + '?page=1'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('coaches', response.context)


class CoachDetailViewTest(TestCase):
    """Test cases for coach_details view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='coach1',
            first_name='Jane',
            last_name='Smith',
            password='pass'
        )
        self.coach = CoachProfile.objects.create(
            user=self.user,
            bio='Professional coach',
            rating=4.8,
            verified=True
        )
    
    def test_coach_details_view(self):
        """Test coach details view"""
        response = self.client.get(
            reverse('courses_and_coach:coach_details', args=[self.coach.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane')
        self.assertContains(response, 'Professional coach')
    
    def test_coach_details_not_found(self):
        """Test coach details with invalid ID"""
        response = self.client.get(
            reverse('courses_and_coach:coach_details', args=[99999])
        )
        self.assertEqual(response.status_code, 404)
    
    def test_coach_details_shows_courses(self):
        """Test coach details shows their courses"""
        category = Category.objects.create(name='Test')
        course = Course.objects.create(
            coach=self.coach,
            category=category,
            title='Coach Course',
            description='Test',
            price=100000,
            duration=60
        )
        
        response = self.client.get(
            reverse('courses_and_coach:coach_details', args=[self.coach.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('courses', response.context)
