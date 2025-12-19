from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.utils.html import strip_tags
import json
from .models import Course, Category
from user_profile.models import CoachProfile


def api_coaches_list(request):
    coaches = CoachProfile.objects.select_related("user").all()

    search = request.GET.get("search", "").strip()
    if search:
        coaches = coaches.filter(
            Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__username__icontains=search)
            | Q(bio__icontains=search)
        )

    expertise_filter = request.GET.get("expertise", "").strip()
    if expertise_filter:
        filtered_ids = []
        for coach in coaches:
            if coach.expertise:
                for exp in coach.expertise:
                    if isinstance(exp, str) and expertise_filter.lower() in exp.lower():
                        filtered_ids.append(coach.id)
                        break
        coaches = coaches.filter(id__in=filtered_ids)

    verified = request.GET.get("verified", "").strip().lower()
    if verified in ["true", "1", "yes"]:
        coaches = coaches.filter(verified=True)
    elif verified in ["false", "0", "no"]:
        coaches = coaches.filter(verified=False)

    sort = request.GET.get("sort", "-created_at")
    valid_sorts = [
        "rating",
        "-rating",
        "total_minutes_coached",
        "-total_minutes_coached",
        "created_at",
        "-created_at",
        "rating_count",
        "-rating_count",
    ]
    if sort in valid_sorts:
        coaches = coaches.order_by(sort)
    else:
        coaches = coaches.order_by("-created_at")

    page = request.GET.get("page", 1)
    page_size = min(int(request.GET.get("page_size", 12)), 100)

    paginator = Paginator(coaches, page_size)
    page_obj = paginator.get_page(page)

    coaches_data = []
    for coach in page_obj:
        coaches_data.append(
            {
                "id": coach.id,
                "username": coach.user.username,
                "first_name": coach.user.first_name,
                "last_name": coach.user.last_name,
                "full_name": coach.user.get_full_name(),
                "bio": coach.bio,
                "expertise": coach.expertise,
                "profile_image_url": coach.image_url,
                "rating": coach.rating,
                "rating_count": coach.rating_count,
                "total_minutes_coached": coach.total_minutes_coached,
                "total_hours_coached": coach.total_hours_coached,
                "total_hours_coached_formatted": coach.total_hours_coached_formatted,
                "balance": coach.balance,
                "verified": coach.verified,
                "created_at": coach.created_at.isoformat(),
                "updated_at": coach.updated_at.isoformat(),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "data": coaches_data,
            "pagination": {
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "page_size": page_size,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
        }
    )


def api_coach_detail(request, coach_id):
    try:
        coach = CoachProfile.objects.select_related("user").get(id=coach_id)
    except CoachProfile.DoesNotExist:
        return JsonResponse({"success": False, "error": "Coach not found"}, status=404)

    courses = Course.objects.filter(coach=coach).select_related("category")
    courses_data = []
    for course in courses:
        courses_data.append(
            {
                "id": course.id,
                "title": course.title,
                "category": {
                    "id": course.category.id if course.category else None,
                    "name": course.category.name if course.category else None,
                },
                "price": course.price,
                "price_formatted": course.price_formatted,
                "duration": course.duration,
                "duration_formatted": course.duration_formatted,
                "rating": course.rating,
                "rating_count": course.rating_count,
                "thumbnail_url": course.thumbnail_url,
            }
        )

    coach_data = {
        "id": coach.id,
        "username": coach.user.username,
        "first_name": coach.user.first_name,
        "last_name": coach.user.last_name,
        "full_name": coach.user.get_full_name(),
        "email": coach.user.email,
        "bio": coach.bio,
        "expertise": coach.expertise,
        "profile_image_url": coach.image_url,
        "rating": coach.rating,
        "rating_count": coach.rating_count,
        "total_minutes_coached": coach.total_minutes_coached,
        "total_hours_coached": coach.total_hours_coached,
        "total_hours_coached_formatted": coach.total_hours_coached_formatted,
        "balance": coach.balance,
        "verified": coach.verified,
        "created_at": coach.created_at.isoformat(),
        "updated_at": coach.updated_at.isoformat(),
        "courses": courses_data,
        "total_courses": len(courses_data),
    }

    return JsonResponse({"success": True, "data": coach_data})


def api_courses_list(request):
    courses = Course.objects.select_related("coach", "category", "coach__user").all()

    search = request.GET.get("search", "").strip()
    if search:
        courses = courses.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    category_filter = request.GET.get("category", "").strip()
    if category_filter:
        courses = courses.filter(category__name__iexact=category_filter)

    coach_id = request.GET.get("coach_id", "").strip()
    if coach_id:
        try:
            courses = courses.filter(coach_id=int(coach_id))
        except ValueError:
            pass

    min_price = request.GET.get("min_price", "").strip()
    if min_price:
        try:
            courses = courses.filter(price__gte=int(min_price))
        except ValueError:
            pass

    max_price = request.GET.get("max_price", "").strip()
    if max_price:
        try:
            courses = courses.filter(price__lte=int(max_price))
        except ValueError:
            pass

    min_rating = request.GET.get("min_rating", "").strip()
    if min_rating:
        try:
            courses = courses.filter(rating__gte=float(min_rating))
        except ValueError:
            pass

    sort = request.GET.get("sort", "-created_at")
    valid_sorts = [
        "price",
        "-price",
        "rating",
        "-rating",
        "created_at",
        "-created_at",
        "duration",
        "-duration",
        "title",
        "-title",
    ]
    if sort in valid_sorts:
        courses = courses.order_by(sort)
    else:
        courses = courses.order_by("-created_at")

    page = request.GET.get("page", 1)
    page_size = min(int(request.GET.get("page_size", 12)), 100)

    paginator = Paginator(courses, page_size)
    page_obj = paginator.get_page(page)

    courses_data = []
    for course in page_obj:
        courses_data.append(
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "location": course.location,
                "price": course.price,
                "price_formatted": course.price_formatted,
                "duration": course.duration,
                "duration_formatted": course.duration_formatted,
                "rating": course.rating,
                "rating_count": course.rating_count,
                "thumbnail_url": course.thumbnail_url,
                "created_at": course.created_at.isoformat(),
                "updated_at": course.updated_at.isoformat(),
                "category": {
                    "id": course.category.id if course.category else None,
                    "name": course.category.name if course.category else None,
                    "description": course.category.description
                    if course.category
                    else None,
                    "thumbnail_url": course.category.thumbnail_url
                    if course.category
                    else None,
                }
                if course.category
                else None,
                "coach": {
                    "id": course.coach.id,
                    "username": course.coach.user.username,
                    "first_name": course.coach.user.first_name,
                    "last_name": course.coach.user.last_name,
                    "full_name": course.coach.user.get_full_name(),
                    "profile_image_url": course.coach.image_url,
                    "rating": course.coach.rating,
                    "verified": course.coach.verified,
                },
            }
        )

    return JsonResponse(
        {
            "success": True,
            "data": courses_data,
            "pagination": {
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "page_size": page_size,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
        }
    )


def api_course_detail(request, course_id):
    try:
        course = Course.objects.select_related("coach", "category", "coach__user").get(
            id=course_id
        )
    except Course.DoesNotExist:
        return JsonResponse({"success": False, "error": "Course not found"}, status=404)

    related_courses = (
        Course.objects.filter(category=course.category)
        .exclude(id=course.id)
        .select_related("coach__user")[:4]
    )

    related_courses_data = []
    for related in related_courses:
        related_courses_data.append(
            {
                "id": related.id,
                "title": related.title,
                "price": related.price,
                "price_formatted": related.price_formatted,
                "duration": related.duration,
                "duration_formatted": related.duration_formatted,
                "rating": related.rating,
                "thumbnail_url": related.thumbnail_url,
            }
        )

    course_data = {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "location": course.location,
        "price": course.price,
        "price_formatted": course.price_formatted,
        "duration": course.duration,
        "duration_formatted": course.duration_formatted,
        "rating": course.rating,
        "rating_count": course.rating_count,
        "thumbnail_url": course.thumbnail_url,
        "created_at": course.created_at.isoformat(),
        "updated_at": course.updated_at.isoformat(),
        "category": {
            "id": course.category.id if course.category else None,
            "name": course.category.name if course.category else None,
            "description": course.category.description if course.category else None,
            "thumbnail_url": course.category.thumbnail_url if course.category else None,
        }
        if course.category
        else None,
        "coach": {
            "id": course.coach.id,
            "username": course.coach.user.username,
            "first_name": course.coach.user.first_name,
            "last_name": course.coach.user.last_name,
            "full_name": course.coach.user.get_full_name(),
            "bio": course.coach.bio,
            "expertise": course.coach.expertise,
            "profile_image_url": course.coach.image_url,
            "rating": course.coach.rating,
            "rating_count": course.coach.rating_count,
            "total_hours_coached_formatted": course.coach.total_hours_coached_formatted,
            "verified": course.coach.verified,
        },
        "related_courses": related_courses_data,
    }

    return JsonResponse({"success": True, "data": course_data})


def api_categories_list(request):
    categories = Category.objects.all()

    categories_data = []
    for category in categories:
        # Count courses in this category
        course_count = Course.objects.filter(category=category).count()

        categories_data.append(
            {
                "id": category.id,
                "name": category.name,
                "description": category.description,
                "thumbnail_url": category.thumbnail_url,
                "course_count": course_count,
            }
        )

    return JsonResponse(
        {
            "success": True,
            "data": categories_data,
            "total_count": len(categories_data),
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_create_course(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            return JsonResponse(
                {"status": "error", "message": "Authentication required"}, status=401
            )

        try:
            data = json.loads(request.body)

            try:
                coach_profile = request.user.coachprofile
            except CoachProfile.DoesNotExist:
                return JsonResponse(
                    {"status": "error", "message": "User is not a coach"}, status=403
                )

            try:
                category = Category.objects.get(id=int(data["category_id"]))
            except (Category.DoesNotExist, ValueError, KeyError):
                return JsonResponse(
                    {"status": "error", "message": "Invalid category"}, status=404
                )

            new_course = Course.objects.create(
                coach=coach_profile,
                title=strip_tags(data["title"]),
                description=strip_tags(data["description"]),
                price=float(data["price"]),
                duration=int(data["duration"]),
                category=category,
                location=strip_tags(data["location"]),
                thumbnail_url=strip_tags(data.get("thumbnail_url", "")),
            )

            new_course.save()

            return JsonResponse(
                {
                    "status": "success",
                    "message": "Course created successfully",
                    "course_id": new_course.id,
                },
                status=200,
            )
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid method"}, status=401)


@csrf_exempt
@require_http_methods(["POST"])
def api_edit_course(request, course_id):
    # Check authentication
    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "error": "Authentication required"}, status=401
        )

    # Check if user has coach profile
    try:
        coach_profile = request.user.coachprofile
    except CoachProfile.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "error": "Access denied. Only coaches can edit courses.",
            },
            status=403,
        )

    # Get course
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return JsonResponse({"success": False, "error": "Course not found"}, status=404)

    # Check ownership
    if course.coach != coach_profile:
        return JsonResponse(
            {"success": False, "error": "You are not authorized to edit this course"},
            status=403,
        )

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "error": "Invalid JSON data"}, status=400
        )

    # Update category if provided
    if "category_id" in data:
        try:
            category = Category.objects.get(id=data["category_id"])
            course.category = category
        except Category.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Category not found"}, status=404
            )

    # Update other fields if provided
    if "title" in data:
        course.title = data["title"]
    if "description" in data:
        course.description = data["description"]
    if "location" in data:
        course.location = data["location"]
    if "thumbnail_url" in data:
        course.thumbnail_url = data["thumbnail_url"]

    # Validate and update price
    if "price" in data:
        try:
            price = int(data["price"])
            if price < 0:
                raise ValueError("Price must be positive")
            course.price = price
        except (ValueError, TypeError):
            return JsonResponse(
                {"success": False, "error": "Invalid price"}, status=400
            )

    # Validate and update duration
    if "duration" in data:
        try:
            duration = int(data["duration"])
            if duration < 0:
                raise ValueError("Duration must be positive")
            course.duration = duration
        except (ValueError, TypeError):
            return JsonResponse(
                {"success": False, "error": "Invalid duration"}, status=400
            )

    course.save()

    return JsonResponse(
        {
            "success": True,
            "message": "Course updated successfully",
            "data": {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "location": course.location,
                "price": course.price,
                "price_formatted": course.price_formatted,
                "duration": course.duration,
                "duration_formatted": course.duration_formatted,
                "thumbnail_url": course.thumbnail_url,
                "category": {
                    "id": course.category.id if course.category else None,
                    "name": course.category.name if course.category else None,
                },
                "updated_at": course.updated_at.isoformat(),
            },
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def api_delete_course(request, course_id):
    # Check authentication
    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "error": "Authentication required"}, status=401
        )

    # Check if user has coach profile
    try:
        coach_profile = request.user.coachprofile
    except CoachProfile.DoesNotExist:
        return JsonResponse(
            {
                "success": False,
                "error": "Access denied. Only coaches can delete courses.",
            },
            status=403,
        )

    # Get course
    try:
        course = Course.objects.get(id=course_id)
    except Course.DoesNotExist:
        return JsonResponse({"success": False, "error": "Course not found"}, status=404)

    # Check ownership
    if course.coach != coach_profile:
        return JsonResponse(
            {"success": False, "error": "You are not authorized to delete this course"},
            status=403,
        )

    course_title = course.title
    course.delete()

    return JsonResponse(
        {
            "success": True,
            "message": f"Course '{course_title}' deleted successfully",
        }
    )


def api_my_courses(request):
    # Check if user has coach profile
    try:
        coach_profile = request.user.coachprofile
    except (CoachProfile.DoesNotExist, AttributeError):
        return JsonResponse(
            {
                "success": False,
                "message": "Access denied. Only coaches can view this page.",
            },
            status=403,
        )

    courses = (
        Course.objects.filter(coach=coach_profile)
        .select_related("category")
        .order_by("-created_at")
    )

    # Pagination
    page = request.GET.get("page", 1)
    page_size = min(int(request.GET.get("page_size", 12)), 100)

    paginator = Paginator(courses, page_size)
    page_obj = paginator.get_page(page)

    courses_data = []
    for course in page_obj:
        courses_data.append(
            {
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "location": course.location,
                "price": course.price,
                "price_formatted": course.price_formatted,
                "duration": course.duration,
                "duration_formatted": course.duration_formatted,
                "rating": course.rating,
                "rating_count": course.rating_count,
                "thumbnail_url": course.thumbnail_url,
                "created_at": course.created_at.isoformat(),
                "updated_at": course.updated_at.isoformat(),
                "category": {
                    "id": course.category.id if course.category else None,
                    "name": course.category.name if course.category else None,
                },
            }
        )

    return JsonResponse(
        {
            "success": True,
            "data": courses_data,
            "pagination": {
                "current_page": page_obj.number,
                "total_pages": paginator.num_pages,
                "total_count": paginator.count,
                "page_size": page_size,
                "has_next": page_obj.has_next(),
                "has_previous": page_obj.has_previous(),
            },
        }
    )
