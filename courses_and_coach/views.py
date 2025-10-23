from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Course, Category
from .forms import CourseForm
from user_profile.models import CoachProfile


def show_courses(request):
    courses = Course.objects.all().select_related("coach", "category")
    categories = Category.objects.all()

    # Filter by category
    category_filter = request.GET.get("category")
    if category_filter:
        courses = courses.filter(category__id=category_filter)

    # Search functionality
    search_query = request.GET.get("search")
    if search_query:
        courses = courses.filter(title__icontains=search_query)

    # Pagination
    paginator = Paginator(courses, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "courses": page_obj,
        "categories": categories,
        "selected_category": category_filter,
        "search_query": search_query,
    }
    return render(request, "courses_and_coach/courses/courses_list.html", context)


def course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    related_courses = Course.objects.filter(category=course.category).exclude(
        id=course.id
    )[:4]

    context = {
        "course": course,
        "related_courses": related_courses,
    }
    return render(request, "courses_and_coach/courses/courses_details.html", context)


@login_required(login_url="user_profile:login")
def create_course(request):
    # Check if user has coach profile
    try:
        coach_profile = request.user.coachprofile
    except CoachProfile.DoesNotExist:
        messages.error(
            request, "Anda harus menjadi coach terverifikasi untuk membuat kelas."
        )
        return redirect("courses_and_coach:show_courses")

    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save(commit=False)
            course.coach = coach_profile
            course.save()
            messages.success(request, "Kelas berhasil dibuat!")
            return redirect("courses_and_coach:course_details", course_id=course.id)
    else:
        form = CourseForm()

    context = {
        "form": form,
        "coach_profile": coach_profile,
    }
    return render(request, "courses_and_coach/courses/create_course.html", context)


@login_required(login_url="user_profile:login")
def my_courses(request):
    # Check if user has coach profile
    try:
        coach_profile = request.user.coachprofile
        courses = Course.objects.filter(coach=coach_profile).order_by("-created_at")
    except CoachProfile.DoesNotExist:
        messages.error(request, "Anda belum terdaftar sebagai coach.")
        return redirect("courses_and_coach:show_courses")

    from datetime import date
    
    context = {
        "courses": courses,
        "coach_profile": coach_profile,
        "today": date.today(),  # Add today for modal date picker min value
    }
    return render(request, "courses_and_coach/courses/my_courses.html", context)
