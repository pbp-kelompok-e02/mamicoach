from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.messages import get_messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .forms import TraineeRegistrationForm, CoachRegistrationForm
from .models import CoachProfile, Certification


def register_user(request):
    if request.method == "POST":
        form = TraineeRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
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
    if request.method == "POST":
        form = CoachRegistrationForm(request.POST)
        if form.is_valid():
            expertise_list = request.POST.getlist('expertise[]')
            
            if not expertise_list:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'errors': {'expertise': ['Please select at least one expertise area.']}
                    }, status=400)
                
                messages.error(request, "Please select at least one expertise area.")
                context = {"form": form}
                return render(request, "register_coach.html", context)
            
            user = form.save()
            
            coach_profile = CoachProfile.objects.create(
                user=user,
                bio=form.cleaned_data['bio'],
                expertise=expertise_list,
                image_url=form.cleaned_data.get('image_url', '')
            )
            
            cert_names = request.POST.getlist('certification_name[]')
            cert_urls = request.POST.getlist('certification_url[]')
            
            for name, url in zip(cert_names, cert_urls):
                if name.strip() and url.strip():
                    Certification.objects.create(
                        coach=coach_profile,
                        certificate_name=name.strip(),
                        file_url=url.strip(),
                        verified=False
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
    
    context = {"form": form}
    return render(request, "register_coach.html", context)


def login_user(request):
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