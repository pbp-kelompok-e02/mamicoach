from django.urls import path
from .views import create_review, edit_review, show_sample_review

app_name = "reviews"

urlpatterns = [
    path("create_review/", create_review, name="create_review"),
    path("edit_review/", edit_review, name="edit_review"),
    path("sample/", show_sample_review, name="sample_review"),
]
