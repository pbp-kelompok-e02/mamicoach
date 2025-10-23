from django.shortcuts import render
from reviews.models import Review


# Create your views here.
def show_main(request):
    # Fetch top 10 reviews by highest rating
    top_reviews = Review.objects.select_related(
        'user', 'course', 'coach', 'coach__user'
    ).order_by('-rating', '-created_at')[:10]
    
    ctx = {
        'top_reviews': top_reviews,
    }
    return render(request, "pages/landing_page/index.html", context=ctx)
