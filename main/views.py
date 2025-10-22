from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login as auth_login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from main.forms import RegisterForm


# Create your views here.
@login_required(login_url='main:login')
def show_main(request):
    return render(request, "pages/main.html")


def register(request):
    form = RegisterForm()

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account successfully created!")
            return redirect("main:login")
    context = {"form": form}
    return render(request, "pages/register.html", context)


def login_user(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)

        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('main:show_main')
    else:
        form = AuthenticationForm(request)
    
    context = {'form': form}
    return render(request, 'pages/login.html', context)