from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .models import Course, Category
from .forms import CourseForm
from user_profile.models import CoachProfile
from django.http import JsonResponse
from django.template.loader import render_to_string
from reviews.models import Review


def show_courses(request):
    courses = Course.objects.all().select_related("coach", "category")
    categories = Category.objects.all()

    # Filter by category
    category_filter = request.GET.get("category")
    if category_filter:
        courses = courses.filter(category__name=category_filter)

    # Search functionality
    search_query = request.GET.get("search")
    if search_query:
        courses = courses.filter(title__icontains=search_query)

    # Pagination
    paginator = Paginator(courses, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "courses": page_obj,
        "categories": categories,
        "selected_category": category_filter,
        "search_query": search_query,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
    }
    return render(request, "courses_and_coach/courses_list.html", context)


def course_details(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    related_courses = Course.objects.filter(category=course.category).exclude(
        id=course.pk
    )[:4]

    # Fetch reviews for this course
    reviews = (
        Review.objects.filter(course=course)
        .select_related("user", "coach", "coach__user")
        .order_by("-created_at")
    )

    context = {
        "course": course,
        "related_courses": related_courses,
        "reviews": reviews,
    }
    return render(request, "courses_and_coach/courses/courses_details.html", context)


@login_required(login_url="user_profile:login")
def create_course(request):
    # Check if user has coach profile
    try:
        coach_profile = request.user.coachprofile
    except CoachProfile.DoesNotExist:
        messages.error(
            request, "Only coaches can create courses. Please create a coach account."
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


def category_detail(request, category_name):
    category = get_object_or_404(Category, name__iexact=category_name)
    all_courses_in_category = Course.objects.filter(category=category).select_related("coach")
    
    courses = all_courses_in_category

    search_query = request.GET.get("search")
    if search_query:
        courses = courses.filter(title__icontains=search_query)

    paginator = Paginator(courses, 12)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Count coaches by their expertise (category name in their expertise list)
    coaches_with_expertise = CoachProfile.objects.all()
    coaches_count = 0
    category_name_lower = category.name.lower()
    for coach in coaches_with_expertise:
        if coach.expertise:
            for expertise in coach.expertise:
                if isinstance(expertise, str) and expertise.lower() == category_name_lower:
                    coaches_count += 1
                    break

    context = {
        "category": category,
        "courses": page_obj,
        "search_query": search_query,
        "courses_count": courses.count(),
        "coaches_count": coaches_count,
    }
    return render(request, "courses_and_coach/category_detail.html", context)


@login_required(login_url="user_profile:login")
def my_courses(request):
    # Check if user has coach profile
    try:
        coach_profile = request.user.coachprofile
        courses = Course.objects.filter(coach=coach_profile).order_by("-created_at")
    except CoachProfile.DoesNotExist:
        messages.error(request, "Access denied. Only coaches can view this page.")
        return redirect("courses_and_coach:show_courses")

    from datetime import date

    context = {
        "courses": courses,
        "coach_profile": coach_profile,
        "today": date.today(),  # Add today for modal date picker min value
    }
    return render(request, "courses_and_coach/courses/my_courses.html", context)


def courses_ajax(request):
    courses_list = Course.objects.all()

    search_query = request.GET.get("search")
    if search_query:
        courses_list = courses_list.filter(title__icontains=search_query)

    category_detail = request.GET.get("category")
    if category_detail:
        courses_list = courses_list.filter(category__name__iexact=category_detail)

    page = request.GET.get("page", 1)
    paginator = Paginator(courses_list, 12)  # 12 courses per page
    page_obj = paginator.get_page(page)

    data = [
        {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "coach": course.coach.user.get_full_name(),
            "category": course.category.name if course.category else None,
            "price": course.price,
            "duration": course.duration,
            "location": course.location,
            "rating": 4,  # Placeholder for future rating feature
            "thumbnail_url": course.thumbnail_url,
        }
        for course in page_obj
    ]

    return JsonResponse({"courses": data})


def courses_card_ajax(request):
    courses_list = Course.objects.all()

    search_query = request.GET.get("search")
    if search_query:
        courses_list = courses_list.filter(title__icontains=search_query)

    category_detail = request.GET.get("category")
    if category_detail:
        courses_list = courses_list.filter(category__name__iexact=category_detail)

    page = request.GET.get("page", 1)
    paginator = Paginator(courses_list, 12)  # 12 courses per page
    page_obj = paginator.get_page(page)

    html = "".join(
        render_to_string(
            "courses_and_coach/partials/course_card.html", {"course": course}
        )
        for course in page_obj
    )

    return JsonResponse(
        {
            "total_count": paginator.count,
            "count": len(page_obj),
            "html": html,
            "current_page": page_obj.number,
            "total_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
    )


def courses_by_id_ajax(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    data = {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "coach": course.coach.user.get_full_name(),
        "category": course.category.name if course.category else None,
        "price": course.price,
        "duration": course.duration,
        "thumbnail_url": course.thumbnail_url,
    }

    return JsonResponse({"course": data})


@login_required(login_url="user_profile:login")
def edit_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    # Ensure the logged-in user is the coach who created the course
    try:
        coach_profile = request.user.coachprofile
    except CoachProfile.DoesNotExist:
        messages.error(request, "Access denied. Only coaches can edit courses.")
        return redirect("courses_and_coach:show_courses")

    if course.coach != coach_profile:
        messages.error(request, "Anda tidak berwenang mengedit kelas ini.")
        return redirect("courses_and_coach:course_details", course_id=course.id)

    if request.method == "POST":
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, "Kelas berhasil diperbarui.")
            return redirect("courses_and_coach:course_details", course_id=course.id)
    else:
        form = CourseForm(instance=course)

    context = {"form": form, "course": course}
    return render(request, "courses_and_coach/courses/edit_course.html", context)


@login_required(login_url="user_profile:login")
def delete_course(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    try:
        coach_profile = request.user.coachprofile
    except CoachProfile.DoesNotExist:
        messages.error(request, "Access denied. Only coaches can delete courses.")
        return redirect("courses_and_coach:show_courses")

    if course.coach != coach_profile:
        messages.error(request, "Anda tidak berwenang menghapus kelas ini.")
        return redirect("courses_and_coach:course_details", course_id=course.id)

    if request.method == "POST":
        course.delete()
        messages.success(request, "Kelas berhasil dihapus.")
        # If request is AJAX, return JSON
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            from django.urls import reverse

            return JsonResponse(
                {"success": True, "redirect": reverse("courses_and_coach:my_courses")}
            )
        return redirect("courses_and_coach:my_courses")

    context = {"course": course}
    return render(request, "courses_and_coach/courses/confirm_delete.html", context)


def show_coaches(request):
    coaches = CoachProfile.objects.all()

    search_query = request.GET.get("search")
    if search_query:
        coaches = (
            coaches.filter(user__first_name__icontains=search_query)
            | coaches.filter(user__last_name__icontains=search_query)
            | coaches.filter(user__username__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(coaches, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    context = {
        "coaches": page_obj,
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,
        "search_query": search_query,
    }
    return render(request, "courses_and_coach/coaches_list.html", context)


def coaches_card_ajax(request):
    coaches_list = CoachProfile.objects.all()

    # Filter by category (expertise) if provided
    category_filter = request.GET.get("category")
    if category_filter:
        # Filter coaches whose expertise contains the category name (case-insensitive)
        filtered_coaches = []
        for coach in coaches_list:
            if coach.expertise:
                for expertise in coach.expertise:
                    if isinstance(expertise, str) and expertise.lower() == category_filter.lower():
                        filtered_coaches.append(coach.id)
                        break
        coaches_list = coaches_list.filter(id__in=filtered_coaches)

    search_query = request.GET.get("search")
    if search_query:
        coaches_list = (
            coaches_list.filter(user__first_name__icontains=search_query)
            | coaches_list.filter(user__last_name__icontains=search_query)
            | coaches_list.filter(user__username__icontains=search_query)
        )

    page = request.GET.get("page", 1)
    paginator = Paginator(coaches_list, 12)
    page_obj = paginator.get_page(page)

    html = "".join(
        render_to_string("courses_and_coach/partials/coach_card.html", {"coach": coach})
        for coach in page_obj
    )

    return JsonResponse(
        {
            "total_count": paginator.count,
            "count": len(page_obj),
            "html": html,
            "current_page": page_obj.number,
            "total_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "has_previous": page_obj.has_previous(),
        }
    )


def coach_details(request, coach_id):
    coach = get_object_or_404(CoachProfile, id=coach_id)
    courses = Course.objects.filter(coach=coach)
    coach_reviews = Review.objects.filter(coach=coach).select_related('user', 'course').order_by('-created_at')

    context = {
        "coach": coach,
        "courses": courses,
        "coach_reviews": coach_reviews,
    }
    return render(request, "courses_and_coach/coaches/coach_details.html", context)
