from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# Create your views here.
def show_main(request):
    return render(request, "pages/main.html")