from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.messages import get_messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .forms import TraineeRegistrationForm, CoachRegistrationForm
from .models import CoachProfile, Certification, UserProfile


def register_user(request):
    if request.user.is_authenticated:
        return redirect('main:show_main')
    if request.method == "POST":
        form = TraineeRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create UserProfile for the new user
            UserProfile.objects.create(user=user)
            
            # Ajax Request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Account successfully created!',
                    'redirect_url': reverse('user_profile:login')
                })
            
            messages.success(request, "Account successfully created!")
            return redirect("user_profile:login")
        else:
            # Ajax Request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]
                return JsonResponse({
                    'success': False,
                    'errors': errors
                }, status=400)
    else:
        form = TraineeRegistrationForm()
    
    context = {"form": form}
    return render(request, "register.html", context)


def register_coach(request):
    if request.user.is_authenticated:
        return redirect('main:show_main')
    from courses_and_coach.models import Category
    
    if request.method == "POST":
        form = CoachRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            expertise_list = request.POST.getlist('expertise[]')
            
            if not expertise_list:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'errors': {'expertise': ['Please select at least one expertise area.']}
                    }, status=400)
                
                messages.error(request, "Please select at least one expertise area.")
                categories = Category.objects.all().order_by('name')
                context = {"form": form, "categories": categories}
                return render(request, "register_coach.html", context)
            
            user = form.save()
            
            coach_profile = CoachProfile.objects.create(
                user=user,
                bio=form.cleaned_data['bio'],
                expertise=expertise_list,
                profile_image=form.cleaned_data.get('profile_image')
            )
            
            cert_names = request.POST.getlist('certification_name[]')
            cert_urls = request.POST.getlist('certification_url[]')
            
            for name, url in zip(cert_names, cert_urls):
                if name.strip() and url.strip():
                    Certification.objects.create(
                        coach=coach_profile,
                        certificate_name=name.strip(),
                        file_url=url.strip(),
                        status='pending'
                    )
            
            # Ajax Request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Coach account successfully created!',
                    'redirect_url': reverse('user_profile:login')
                })
            
            messages.success(request, "Coach account successfully created!")
            return redirect("user_profile:login")
        else:
            # Ajax Request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {}
                for field, error_list in form.errors.items():
                    errors[field] = [str(error) for error in error_list]
                return JsonResponse({
                    'success': False,
                    'errors': errors
                }, status=400)
    else:
        form = CoachRegistrationForm()
    
    categories = Category.objects.all().order_by('name')
    context = {"form": form, "categories": categories}
    return render(request, "register_coach.html", context)


def login_user(request):
    if request.user.is_authenticated:
        return redirect('main:show_main')
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        from_modal = request.POST.get('from_modal', 'false') == 'true'

        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # Ajax Request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': f'Welcome back, {user.first_name} {user.last_name}!',
                    'redirect_url': reverse('main:show_main')
                })
            
            next_url = request.GET.get('next', 'main:show_main')
            return redirect(next_url)
        else:
            # Ajax Request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Username atau password salah. Silakan coba lagi.'
                }, status=400)
            
            messages.error(request, "Username atau password salah. Silakan coba lagi.")
            
            if from_modal:
                referer = request.META.get('HTTP_REFERER', '/')
                separator = '&' if '?' in referer else '?'
                return redirect(f"{referer}{separator}login_error=1")
    else:
        form = AuthenticationForm(request)
    
    context = {'form': form}
    return render(request, 'login.html', context)


def logout_user(request):
    # Ajax Request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        logout(request)
        response = JsonResponse({
            'success': True,
            'message': 'You have been logged out successfully.',
            'redirect_url': reverse('main:show_main')
        })
        response.delete_cookie('last_login')
        return response
    
    logout(request)
    response = HttpResponseRedirect(reverse('main:show_main'))
    response.delete_cookie('last_login')
    return response


@login_required
def dashboard_coach(request):
    try:
        coach_profile = CoachProfile.objects.get(user=request.user)
    except CoachProfile.DoesNotExist:
        messages.error(request, "Access denied. This page is only for coaches.")
        return redirect('main:show_main')
    
    certifications = Certification.objects.filter(coach=coach_profile)
    
    context = {
        'coach_profile': coach_profile,
        'certifications': certifications,
    }
    return render(request, 'dashboard_coach.html', context)


@login_required
def get_coach_profile(request):
    from booking.models import Booking
    from chat.models import ChatSession
    from django.utils import timezone
    
    try:
        coach_profile = CoachProfile.objects.get(user=request.user)
        certifications = Certification.objects.filter(coach=coach_profile)
        
        # Get bookings with different statuses
        confirmed_bookings = Booking.objects.filter(
            coach=coach_profile,
            status='confirmed'
        ).select_related('user', 'course', 'schedule')
        
        # Pending bookings include both 'pending' and 'paid' statuses
        pending_bookings = Booking.objects.filter(
            coach=coach_profile,
            status__in=['paid']
        ).select_related('user', 'course', 'schedule')
        
        completed_bookings = Booking.objects.filter(
            coach=coach_profile,
            status='done'
        ).select_related('user', 'course', 'schedule')
        
        # Helper function to format booking data
        def format_booking(booking):
            # Format datetime strings
            start_dt = booking.start_datetime if booking.start_datetime else None
            end_dt = booking.end_datetime if booking.end_datetime else None
            
            start_str = start_dt.strftime('%d %b %H:%M') if start_dt else 'N/A'
            end_str = end_dt.strftime('%d %b %H:%M') if end_dt else 'N/A'
            
            return {
                'id': booking.id,
                'booking_id': booking.id,
                'course_title': booking.course.title,
                'trainee_name': booking.user.get_full_name() or booking.user.username,
                'booking_datetime': f"{start_str} - {end_str}",
                'start_datetime': start_str,
                'end_datetime': end_str,
                'status': booking.status
            }
        
        # Build profile data
        profile_data = {
            'success': True,
            'profile': {
                'full_name': request.user.get_full_name(),
                'initials': f"{request.user.first_name[0]}{request.user.last_name[0]}" if request.user.first_name and request.user.last_name else "??",
                'profile_image': coach_profile.profile_image.url if coach_profile.profile_image else None,
                'expertise': coach_profile.expertise if coach_profile.expertise else [],
                'rating': coach_profile.rating,
                'bio': coach_profile.bio,
                'verified': coach_profile.verified,
                'certifications': [
                    {
                        'id': cert.pk,
                        'name': cert.certificate_name,
                        'url': cert.file_url,
                        'status': cert.status
                    }
                    for cert in certifications
                ],
                'confirmed_bookings': [format_booking(b) for b in confirmed_bookings],
                'pending_bookings': [format_booking(b) for b in pending_bookings],
                'completed_bookings': [format_booking(b) for b in completed_bookings]
            }
        }
        
        return JsonResponse(profile_data)
        
    except CoachProfile.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': "Access denied. This page is only for coaches."
        }, status=403)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def coach_profile(request):
    from courses_and_coach.models import Category
    
    try:
        coach_profile = CoachProfile.objects.get(user=request.user)
    except CoachProfile.DoesNotExist:
        messages.error(request, "Access denied. This page is only for coaches.")
        return redirect('main:show_main')
    
    if request.method == "POST":
        # Update user data
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.save()
        
        coach_profile.bio = request.POST.get('bio', '').strip()
        
        expertise_list = request.POST.getlist('expertise[]')
        if expertise_list:
            coach_profile.expertise = expertise_list
        
        if 'profile_image' in request.FILES:
            coach_profile.profile_image = request.FILES['profile_image']
        
        coach_profile.save()
        
        deleted_cert_ids = request.POST.getlist('deleted_certifications[]')
        if deleted_cert_ids:
            Certification.objects.filter(id__in=deleted_cert_ids, coach=coach_profile).delete()
        
        new_cert_names = request.POST.getlist('new_cert_names[]')
        new_cert_urls = request.POST.getlist('new_cert_urls[]')
        
        for name, url in zip(new_cert_names, new_cert_urls):
            if name.strip() and url.strip():
                Certification.objects.create(
                    coach=coach_profile,
                    certificate_name=name.strip(),
                    file_url=url.strip(),
                    status='pending'
                )
        
        messages.success(request, "Profile updated successfully!")
        return redirect('user_profile:dashboard_coach')
    
    certifications = Certification.objects.filter(coach=coach_profile)
    categories = Category.objects.all().order_by('name')
    
    context = {
        'coach_profile': coach_profile,
        'certifications': certifications,
        'categories': categories,
    }
    return render(request, 'coach_profile.html', context)


@login_required
def dashboard_user(request):
    # Check if user is a coach
    try:
        coach_profile = CoachProfile.objects.get(user=request.user)
        messages.error(request, "Access denied. Coaches cannot access user dashboard.")
        return redirect('user_profile:dashboard_coach')
    except CoachProfile.DoesNotExist:
        pass
    
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'user': request.user,
        'user_profile': user_profile,
    }
    return render(request, 'dashboard_user.html', context)


@login_required
def get_user_profile(request):
    try:
        # Check if user is a coach
        try:
            coach_profile = CoachProfile.objects.get(user=request.user)
            return JsonResponse({
                'success': False,
                'message': "Access denied. Coaches cannot access user dashboard."
            }, status=403)
        except CoachProfile.DoesNotExist:
            pass
        
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Import models for bookings and reviews
        from booking.models import Booking
        from chat.models import ChatSession
        from reviews.models import Review
        
        # Get bookings with different statuses
        confirmed_bookings = Booking.objects.filter(
            user=request.user,
            status='confirmed'
        ).select_related('user', 'course', 'schedule', 'coach')
        
        paid_bookings = Booking.objects.filter(
            user=request.user,
            status='paid'
        ).select_related('user', 'course', 'schedule', 'coach')
        
        pending_bookings = Booking.objects.filter(
            user=request.user,
            status='pending'
        ).select_related('user', 'course', 'schedule', 'coach')
        
        completed_bookings = Booking.objects.filter(
            user=request.user,
            status='done'
        ).select_related('user', 'course', 'schedule', 'coach')
        
        # Helper function to format booking data
        def format_booking(booking):
            # Format datetime strings
            start_dt = booking.start_datetime if booking.start_datetime else None
            end_dt = booking.end_datetime if booking.end_datetime else None
            
            start_str = start_dt.strftime('%d %b %H:%M') if start_dt else 'N/A'
            end_str = end_dt.strftime('%d %b %H:%M') if end_dt else 'N/A'
            
            # Get or create chat session
            chat_session = ChatSession.objects.filter(
                user=request.user,
                coach=booking.coach.user
            ).first()
            
            chat_session_id = str(chat_session.id) if chat_session else None
            
            return {
                'id': booking.id,
                'booking_id': booking.id,
                'course_title': booking.course.title,
                'coach_name': booking.coach.user.get_full_name() or booking.coach.user.username,
                'booking_datetime': f"{start_str} - {end_str}",
                'start_datetime': start_str,
                'end_datetime': end_str,
                'status': booking.status,
                'chat_session_id': chat_session_id
            }
        
        # Helper function to format completed booking with review info
        def format_completed_booking(booking):
            formatted = format_booking(booking)
            
            # Check if review exists
            review = Review.objects.filter(booking=booking).first()
            formatted['has_review'] = review is not None
            if review:
                formatted['review_id'] = review.id
            
            return formatted
        
        # Build profile data
        profile_data = {
            'success': True,
            'profile': {
                'full_name': request.user.get_full_name(),
                'initials': f"{request.user.first_name[0]}{request.user.last_name[0]}" if request.user.first_name and request.user.last_name else "??",
                'profile_image': user_profile.profile_image.url if user_profile.profile_image else None,
                'confirmed_bookings': [format_booking(b) for b in confirmed_bookings],
                'paid_bookings': [format_booking(b) for b in paid_bookings],
                'pending_bookings': [format_booking(b) for b in pending_bookings],
                'completed_bookings': [format_completed_booking(b) for b in completed_bookings]
            }
        }
        
        return JsonResponse(profile_data)
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@login_required
def user_profile(request):
    # Check if user is a coach
    try:
        coach_profile = CoachProfile.objects.get(user=request.user)
        messages.error(request, "Access denied. Coaches cannot access user profile.")
        return redirect('user_profile:coach_profile')
    except CoachProfile.DoesNotExist:
        pass
    
    user_profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == "POST":
        # Update user data
        request.user.first_name = request.POST.get('first_name', '').strip()
        request.user.last_name = request.POST.get('last_name', '').strip()
        request.user.save()
        
        # Update profile image if provided
        if 'profile_image' in request.FILES:
            user_profile.profile_image = request.FILES['profile_image']
            user_profile.save()
        
        # AJAX Request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully!'
            })
        
        messages.success(request, "Profile updated successfully!")
        return redirect('user_profile:dashboard_user')
    
    context = {
        'user': request.user,
        'user_profile': user_profile,
    }
    return render(request, 'user_profile.html', context)