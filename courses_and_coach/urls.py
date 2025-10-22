from django.urls import path

from courses_and_coach.views import show_courses


app_name = "courses_and_coach"

urlpatterns = [
    path("courses/", show_courses, name="show_courses"),
]
