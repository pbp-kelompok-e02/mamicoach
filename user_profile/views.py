from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import TraineeRegistrationForm, CoachRegistrationForm
from .models import CoachProfile


def register_user(request):
    """View untuk registrasi trainee (user biasa) dengan first_name dan last_name"""
    if request.method == "POST":
        form = TraineeRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account successfully created!")
            return redirect("user_profile:login")
    else:
        form = TraineeRegistrationForm()
    
    context = {"form": form}
    return render(request, "register.html", context)


def register_coach(request):
    """View untuk registrasi coach (langsung membuat user + coach profile)"""
    if request.method == "POST":
        form = CoachRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Coach account successfully created!")
            return redirect("user_profile:login")
    else:
        form = CoachRegistrationForm()
    
    context = {"form": form}
    return render(request, "register_coach.html", context)


def login_user(request):
    """View untuk login user"""
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('main:show_main')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm(request)
    
    context = {'form': form}
    return render(request, 'login.html', context)


def logout_user(request):
    """View untuk logout user"""
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    response = HttpResponseRedirect(reverse('user_profile:login'))
    response.delete_cookie('last_login')
    return response