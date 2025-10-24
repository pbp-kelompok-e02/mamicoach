from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from booking.models import Booking
from .models import Review
from .forms import ReviewForm
# Create your views here.

def show_sample_review(request):
    # Fetch all reviews from database, ordered by most recent
    reviews = Review.objects.select_related(
        'user', 'course', 'coach', 'coach__user'
    ).order_by('-created_at')
    
    ctx = {
        'reviews': reviews
    }
    return render(request, "pages/sample_review.html", context=ctx)

@login_required(login_url='/login')
def create_review(request, booking_id):
    try:
        booking = Booking.objects.get(pk=booking_id)
    except Booking.DoesNotExist:
        messages.error(request, "Booking not found.")
        return redirect('main:show_main')
    
    # Permission check: only the user who made the booking can review it
    if booking.user != request.user:
        messages.error(request, "You do not have permission to create a review for this booking.")
        return redirect('main:show_main')
    
    # Check if review already exists for this booking
    if Review.objects.filter(booking=booking).exists():
        messages.error(request, "A review already exists for this booking. Please edit the existing review instead.")
        return redirect('main:show_main')
    
    # Get callback URL from query params
    callback_url = request.GET.get('next', 'main:show_main')
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.course = booking.course
            review.user = request.user
            review.coach = booking.coach
            review.save()
            messages.success(request, "Review created successfully!")
            # Redirect to callback URL or default
            if callback_url.startswith('/'):
                return redirect(callback_url)
            else:
                return redirect(callback_url)
        else:
            # Debug: log form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ReviewForm()
    
    ctx = {
        'booking': booking,
        'form': form,
        'is_edit': False,
        'callback_url': callback_url,
    }
    return render(request, "pages/create_review.html", context=ctx)

@login_required(login_url='/login')
def edit_review(request, review_id):
    try:
        review = Review.objects.get(pk=review_id)
    except Review.DoesNotExist:
        messages.error(request, "Review not found.")
        return redirect('main:show_main')
    
    # Permission check: only the user who created the review can edit it
    if review.user != request.user:
        messages.error(request, "You do not have permission to edit this review.")
        return redirect('main:show_main')
    
    # Get callback URL from query params
    callback_url = request.GET.get('next', 'main:show_main')
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Review updated successfully!")
            # Redirect to callback URL or default
            if callback_url.startswith('/'):
                return redirect(callback_url)
            else:
                return redirect(callback_url)
        else:
            # Debug: log form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ReviewForm(instance=review)
    
    ctx = {
        'review': review,
        'booking': review.booking,
        'form': form,
        'is_edit': True,
        'callback_url': callback_url,
    }
    return render(request, "pages/edit_review.html", context=ctx)

@login_required(login_url='/login')
def delete_review(request, review_id):
    try:
        review = Review.objects.get(pk=review_id)
    except Review.DoesNotExist:
        messages.error(request, "Review not found.")
        return redirect('main:show_main')
    
    # Permission check: only the user who created the review can delete it
    if review.user != request.user:
        messages.error(request, "You do not have permission to delete this review.")
        return redirect('main:show_main')
    
    if request.method == 'POST':
        # Get callback URL from query params
        callback_url = request.GET.get('next', 'main:show_main')
        review.delete()
        messages.success(request, "Review deleted successfully!")
        # Redirect to callback URL or default
        if callback_url.startswith('/'):
            return redirect(callback_url)
        else:
            return redirect(callback_url)
    else:
        messages.error(request, "Invalid request method.")
        return redirect('main:show_main')
