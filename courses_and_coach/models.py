from django.db import models

# TODO: Import CoachProfile
# from coach_app.models import CoachProfile


class Category(models.Model):
    """
    Category model for organizing courses
    """

    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(null=True, blank=True)
    thumbnail_url = models.URLField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Course(models.Model):
    """
    Course model based on the provided table schema
    """

    # TODO: Update this ForeignKey to use the actual CoachProfile model from another app
    coach = models.ForeignKey(
        "coach_app.CoachProfile",
        on_delete=models.CASCADE,
        related_name="courses",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.PositiveIntegerField(
        help_text="Price in the smallest currency unit (e.g., cents, rupiah)"
    )
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    # TODO: Rating between 0.0 to 5.0
    thumbnail_url = models.URLField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["coach"]),
            models.Index(fields=["category"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"{self.title} by {self.coach}"

    @property
    def price_formatted(self):
        return f"Rp {self.price:,}"

    @property
    def duration_formatted(self):
        """Format duration for display"""
        if self.duration >= 60:
            hours = self.duration // 60
            minutes = self.duration % 60
            if minutes > 0:
                return f"{hours}h {minutes}m"
            return f"{hours}h"
        return f"{self.duration}m"
