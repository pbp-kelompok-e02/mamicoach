from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator


class Coach(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='coach_profile')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    image_url = models.URLField(blank=True, null=True)
    certification_links = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    courses: models.Manager

    def __str__(self):
        return f"Coach: {self.user.username}"

    @property
    def certification_count(self):
        return len(self.certification_links or [])

    def update_rating(self):
        avg_rating = (
            self.courses.aggregate(avg=Avg('reviews__rating'))
            .get('avg') or 0
        )
        self.rating = round(avg_rating, 2)
        self.save(update_fields=['rating'])

    class Meta:
        ordering = ['-rating']


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    thumbnailUrl = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class ModeChoices(models.TextChoices):
    ONLINE = 'online', 'Online'
    OFFLINE = 'offline', 'Offline'


class Course(models.Model):
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name='courses')
    title = models.CharField(max_length=255)
    mode = models.CharField(max_length=10, choices=ModeChoices.choices, default=ModeChoices.OFFLINE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='courses')
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal('0.00'))
    description = models.TextField()
    price = models.PositiveIntegerField()
    location = models.CharField(max_length=255)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    thumbnail_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reviews: models.Manager

    def __str__(self):
        return self.title

    def update_rating(self):
        avg_rating = (
            self.reviews.aggregate(avg=Avg('rating'))
            .get('avg') or 0
        )
        self.rating = round(avg_rating, 2)
        self.save(update_fields=['rating'])

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Courses"


class BookingStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'        # Booking created, waiting for user to pay
    PAID = 'paid', 'Paid'                 # Payment successful, funds held by app (escrow)
    CONFIRMED = 'confirmed', 'Confirmed'  # Coach has accepted
    COMPLETED = 'completed', 'Completed'  # Session done, pending fund release
    RELEASED = 'released', 'Released'     # Funds released to coach
    CANCELLED = 'cancelled', 'Cancelled'     # Booking canceled (by coach or system), fund will be refunded


class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='bookings')
    status = models.CharField(max_length=50, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'course')
        indexes = [models.Index(fields=['user']), models.Index(fields=['course'])]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s Booking for {self.course.title}"


class Review(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['course']),
            models.Index(fields=['rating']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} for {self.course.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.course.update_rating()
        self.course.coach.update_rating()


class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    coach = models.ForeignKey(Coach, on_delete=models.CASCADE, related_name='chat_sessions')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='chat_session', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    messages = models.JSONField(default=list, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user']), models.Index(fields=['coach'])]
        ordering = ['-updated_at']

    def __str__(self):
        return f"ChatSession between {self.user.username} and {self.coach.user.username} {'for booking ' + str(self.booking.pk) if self.booking else ''}"
