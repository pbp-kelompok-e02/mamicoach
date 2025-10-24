from django.shortcuts import render
from reviews.models import Review
from courses_and_coach.models import Course, Category
from user_profile.models import CoachProfile


# Create your views here.
def show_main(request):
    # Fetch top 10 reviews by highest rating
    top_reviews = Review.objects.select_related(
        "user", "course", "coach", "coach__user"
    ).order_by("-rating", "-created_at")[:10]

    featured_courses = (
        Course.objects.all()
        .select_related("coach", "category")
        .order_by("-coach__rating")[:4]
    )

    # Get all categories
    categories = Category.objects.all().order_by("name")

    # Get top 6 coaches by rating
    top_coaches = CoachProfile.objects.filter(verified=True).order_by("-rating")[:6]

    context = {
        "featured_courses": featured_courses,
        "categories": categories,
        "top_coaches": top_coaches,
        "top_reviews": top_reviews,
    }
    return render(request, "pages/landing_page/index.html", context)


# Error handlers
def handler_404(request, exception=None):
    """Handle 404 Not Found errors"""
    return render(request, "404.html", status=404)


def handler_500(request):
    """Handle 500 Internal Server errors"""
    return render(request, "500.html", status=500)
