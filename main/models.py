from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator


class Coach(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='coach_profile')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    certification_links = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Coach: {self.user.username}"

    @property
    def certification_count(self):
        return len(self.certification_links or [])

    def update_rating(self):
        from .models import Review  # Avoid circular import
        avg_rating = (
            Review.objects.filter(class_ref__coach=self)
            .aggregate(avg=Avg('rating'))
            .get('avg') or 0
        )
        self.rating = round(avg_rating, 2)
        self.save(update_fields=['rating'])

    class Meta:
        ordering = ['-rating']


class Course(models.Model):
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.PositiveIntegerField()
    location = models.CharField(max_length=255)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    thumbnail_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Courses"


class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    CONFIRMED = 'confirmed', 'Confirmed'
    COMPLETED = 'completed', 'Completed'
    CANCELLED = 'cancelled', 'Cancelled'


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        indexes = [models.Index(fields=['user']), models.Index(fields=['course'])]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s Booking for {self.course.title}"


class Review(models.Model):
    class_ref = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'user')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['class_ref']),
            models.Index(fields=['rating']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} for {self.class_ref.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.class_ref.coach.update_rating()
