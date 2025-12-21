from django.urls import path
from courses_and_coach.views import (
    coach_details,
    coaches_card_ajax,
    courses_ajax,
    courses_by_id_ajax,
    courses_card_ajax,
    show_coaches,
    show_courses,
    course_details,
    create_course,
    my_courses,
    category_detail,
    edit_course,
    delete_course,
)
from courses_and_coach.api_views import (
    api_coaches_list,
    api_coach_detail,
    api_coach_reviews,
    api_courses_list,
    api_course_detail,
    api_course_reviews,
    api_categories_list,
    api_create_course,
    api_edit_course,
    api_delete_course,
    api_my_courses,
)

app_name = "courses_and_coach"

urlpatterns = [
    path("courses/", show_courses, name="show_courses"),
    path("courses/<int:course_id>/", course_details, name="course_details"),
    path("courses/create/", create_course, name="create_course"),
    path("courses/<str:category_name>/", category_detail, name="category_detail"),
    path("my-courses/", my_courses, name="my_courses"),
    path("courses/<int:course_id>/edit/", edit_course, name="edit_course"),
    path("courses/<int:course_id>/delete/", delete_course, name="delete_course"),
    path("courses-ajax/", courses_ajax, name="courses_ajax"),
    path("courses-card-ajax/", courses_card_ajax, name="courses_card_ajax"),
    path(
        "courses-ajax/<int:course_id>/", courses_by_id_ajax, name="courses_by_id_ajax"
    ),
    path("coaches/", show_coaches, name="show_coaches"),
    path("coaches-card-ajax/", coaches_card_ajax, name="coaches_card_ajax"),
    path("coaches/<int:coach_id>/", coach_details, name="coach_details"),
    # API Endpoints
    path("api/coaches/", api_coaches_list, name="api_coaches_list"),
    path("api/coach/<int:coach_id>/", api_coach_detail, name="api_coach_detail"),
    path("api/coach/<int:coach_id>/reviews/", api_coach_reviews, name="api_coach_reviews"),
    path("api/courses/", api_courses_list, name="api_courses_list"),
    path("api/courses/create/", api_create_course, name="api_create_course"),
    path("api/courses/<int:course_id>/", api_course_detail, name="api_course_detail"),
    path("api/courses/<int:course_id>/reviews/", api_course_reviews, name="api_course_reviews"),
    path("api/courses/<int:course_id>/edit/", api_edit_course, name="api_edit_course"),
    path(
        "api/courses/<int:course_id>/delete/",
        api_delete_course,
        name="api_delete_course",
    ),
    path("api/my-courses/", api_my_courses, name="api_my_courses"),
    path("api/categories/", api_categories_list, name="api_categories_list"),
]
