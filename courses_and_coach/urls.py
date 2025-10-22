from django.urls import path
from courses_and_coach.views import (
    courses_ajax,
    courses_by_id_ajax,
    courses_card_ajax,
    show_courses,
    course_details,
    create_course,
    my_courses,
    category_detail,
)

app_name = "courses_and_coach"

urlpatterns = [
    path("courses/", show_courses, name="show_courses"),
    path("courses/<int:course_id>/", course_details, name="course_details"),
    path("courses/create/", create_course, name="create_course"),
    path("courses/<str:category_name>/", category_detail, name="category_detail"),
    path("my-courses/", my_courses, name="my_courses"),
    path("courses-ajax/", courses_ajax, name="courses_ajax"),
    path("courses-card-ajax/", courses_card_ajax, name="courses_card_ajax"),
    path(
        "courses-ajax/<int:course_id>/", courses_by_id_ajax, name="courses_by_id_ajax"
    ),
]
