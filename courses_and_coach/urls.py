from django.urls import path
from courses_and_coach.views import (
    show_courses,
    course_details,
    create_course,
    my_courses,
)

app_name = "courses_and_coach"

urlpatterns = [
    path("courses/", show_courses, name="show_courses"),
    path("courses/<int:course_id>/", course_details, name="course_details"),
    path("courses/create/", create_course, name="create_course"),
    path("my-courses/", my_courses, name="my_courses"),
]
