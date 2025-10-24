from django.db import models
from django.db.models import Avg

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
        # Update course and coach ratings after save
        self.update_ratings()
    
    def update_ratings(self):
        """Update course and coach ratings based on all reviews"""
        # Update course rating and count
        course_avg = Review.objects.filter(course=self.course).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0.0
        course_count = Review.objects.filter(course=self.course).count()
        self.course.rating = float(course_avg)
        self.course.rating_count = course_count
        self.course.save(update_fields=['rating', 'rating_count'])
        
        # Update coach rating and count
        coach_avg = Review.objects.filter(coach=self.coach).aggregate(
            avg_rating=Avg('rating')
        )['avg_rating'] or 0.0
        coach_count = Review.objects.filter(coach=self.coach).count()
        self.coach.rating = float(coach_avg)
        self.coach.rating_count = coach_count
        self.coach.save(update_fields=['rating', 'rating_count'])
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.course.title}"
