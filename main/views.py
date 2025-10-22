from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.forms import UserCreationForm


# Create your views here.
def show_main(request):
    return render(request, "pages/main.html")

def register_user(request):
    form = UserCreationForm()

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account successfully created!")
            return redirect("main:login")
    context = {"form": form}
    return render(request, "pages/register.html", context)

@login_required(login_url='main:login')
def register_coach(request):
    from user_profile.forms import CoachProfileForm

    try:
        from user_profile.models import CoachProfile
        if CoachProfile.objects.filter(user=request.user).exists():
            messages.info(request, "You already have a coach profile!")
            return redirect("main:show_main")
    except:
        pass
    
    if request.method == "POST":
        form = CoachProfileForm(request.POST)
        if form.is_valid():
            coach_profile = form.save(commit=False)
            coach_profile.user = request.user
            coach_profile.save()
            messages.success(request, "Coach profile successfully created!")
            return redirect("main:show_main")
    else:
        form = CoachProfileForm()
    
    context = {"form": form}
    return render(request, "pages/register_coach.html", context)


def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('main:show_main')
    else:
        form = AuthenticationForm(request)
    
    context = {'form': form}
    return render(request, 'pages/login.html', context)

def logout_user(request):
    logout(request)
    response = HttpResponseRedirect(reverse('main:login'))
    response.delete_cookie('last_login')
    return response