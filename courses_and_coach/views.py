from django.shortcuts import render


# Create your views here.
def show_courses(request):
    return render(request, "courses_and_coach/courses_list.html")
