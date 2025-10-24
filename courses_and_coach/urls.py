from django.urls import path
from courses_and_coach.views import (
    coach_details,
    coaches_card_ajax,
    courses_ajax,
    courses_by_id_ajax,
    courses_card_ajax,
    show_coaches,
    courses_ajax,
    courses_by_id_ajax,
    courses_card_ajax,
    show_courses,
    course_details,
    create_course,
    my_courses,
    category_detail,
    edit_course,
    delete_course,
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
    path("courses/<int:course_id>/edit/", edit_course, name="edit_course"),
    path("courses/<int:course_id>/delete/", delete_course, name="delete_course"),
    path("courses-ajax/", courses_ajax, name="courses_ajax"),
    path("courses-card-ajax/", courses_card_ajax, name="courses_card_ajax"),
    path(
        "courses-ajax/<int:course_id>/", courses_by_id_ajax, name="courses_by_id_ajax"
    ),
]
