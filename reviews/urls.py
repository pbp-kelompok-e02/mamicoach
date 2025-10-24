from django.urls import path
from .views import create_review, edit_review, show_sample_review

app_name = "reviews"

urlpatterns = [
    path("review/create/<int:booking_id>", create_review, name="create_review"),
    path("review/edit/<int:review_id>", edit_review, name="edit_review"),
]
