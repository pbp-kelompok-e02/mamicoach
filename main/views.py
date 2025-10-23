from django.shortcuts import render
from django.contrib.auth.decorators import login_required


# Create your views here.
def show_main(request):
    return render(request, "pages/landing_page/index.html")


# Error handlers
def handler_404(request, exception=None):
    """Handle 404 Not Found errors"""
    return render(request, "404.html", status=404)


def handler_500(request):
    """Handle 500 Internal Server errors"""
    return render(request, "500.html", status=500)
