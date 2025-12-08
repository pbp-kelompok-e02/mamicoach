from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json

from booking.models import Booking
from .models import Review
from .forms import ReviewForm
# Create your views here.


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


# AJAX Endpoints with JSON responses

@csrf_exempt
@require_http_methods(["POST"])
def ajax_create_review(request, booking_id):
    """AJAX endpoint to create a review and return JSON response"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    try:
        booking = Booking.objects.get(pk=booking_id)
    except Booking.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Booking not found.'}, status=404)
    
    # Permission check
    if booking.user != request.user:
        return JsonResponse({'success': False, 'error': 'You do not have permission to create a review for this booking.'}, status=403)
    
    # Check if review already exists
    if Review.objects.filter(booking=booking).exists():
        return JsonResponse({'success': False, 'error': 'A review already exists for this booking.'}, status=400)
    
    try:
        data = json.loads(request.body)
        form = ReviewForm(data)
        
        if form.is_valid():
            review = form.save(commit=False)
            review.booking = booking
            review.course = booking.course
            review.user = request.user
            review.coach = booking.coach
            review.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Review created successfully!',
                'review_id': review.id,
                'booking_id': booking.pk
            }, status=201)
        else:
            errors = {field: error_list for field, error_list in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def ajax_edit_review(request, review_id):
    """AJAX endpoint to edit a review and return JSON response"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    try:
        review = Review.objects.get(pk=review_id)
    except Review.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Review not found.'}, status=404)
    
    # Permission check
    if review.user != request.user:
        return JsonResponse({'success': False, 'error': 'You do not have permission to edit this review.'}, status=403)
    
    try:
        data = json.loads(request.body)
        form = ReviewForm(data, instance=review)
        
        if form.is_valid():
            form.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Review updated successfully!',
                'review_id': review.pk
            }, status=200)
        else:
            errors = {field: error_list for field, error_list in form.errors.items()}
            return JsonResponse({'success': False, 'errors': errors}, status=400)
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["DELETE", "POST"])
def ajax_delete_review(request, review_id):
    """AJAX endpoint to delete a review and return JSON response"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    try:
        review = Review.objects.get(pk=review_id)
    except Review.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Review not found.'}, status=404)
    
    # Permission check
    if review.user != request.user:
        return JsonResponse({'success': False, 'error': 'You do not have permission to delete this review.'}, status=403)
    
    try:
        review_id = review.pk
        review.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Review deleted successfully!',
            'review_id': review_id
        }, status=200)
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def ajax_get_review(request, review_id):
    """AJAX endpoint to fetch review details and return JSON response"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    
    try:
        review = Review.objects.get(pk=review_id)
    except Review.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Review not found.'}, status=404)
    
    # Permission check - allow viewing own review or if user is admin
    if review.user != request.user and not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'You do not have permission to view this review.'}, status=403)
    
    try:
        return JsonResponse({
            'success': True,
            'review': {
                'id': review.pk,
                'rating': review.rating,
                'content': review.content,
                'is_anonymous': review.is_anonymous,
                'booking_id': review.booking.pk,
                'course_id': review.course.pk,
                'created_at': review.created_at.isoformat(),
                'updated_at': review.updated_at.isoformat()
            }
        }, status=200)
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
