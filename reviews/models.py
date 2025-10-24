from django.db import models

from courses_and_coach.models import Course
from booking.models import Booking
from django.contrib.auth.models import User
from user_profile.models import CoachProfile

# # Create your models here.
class Review(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    coach = models.ForeignKey(CoachProfile, on_delete=models.CASCADE, related_name='reviews')
    is_anonymous = models.BooleanField(default=False)
    rating = models.PositiveIntegerField()
    content = models.TextField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update course rating
        course_reviews = Review.objects.filter(course=self.course)
        course_avg = course_reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0
        self.course.rating = course_avg
        self.course.save(update_fields=['rating'])

        # Update coach rating
        coach_reviews = Review.objects.filter(coach=self.coach)
        coach_avg = coach_reviews.aggregate(models.Avg('rating'))['rating__avg'] or 0
        self.coach.rating = coach_avg
        self.coach.save(update_fields=['rating'])
