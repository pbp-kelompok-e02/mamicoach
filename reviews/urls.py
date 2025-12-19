from django.urls import path
from .views import (
    create_review,
    edit_review,
    delete_review,
    ajax_create_review,
    ajax_edit_review,
    ajax_delete_review,
    ajax_get_review,
    ajax_list_my_reviews,
)

app_name = "reviews"

urlpatterns = [
    path("review/create/<int:booking_id>", create_review, name="create_review"),
    path("review/edit/<int:review_id>", edit_review, name="edit_review"),
    path("review/delete/<int:review_id>", delete_review, name="delete_review"),
    
    # AJAX endpoints
    path("review/ajax/create/<int:booking_id>", ajax_create_review, name="ajax_create_review"),
    path("review/ajax/edit/<int:review_id>", ajax_edit_review, name="ajax_edit_review"),
    path("review/ajax/delete/<int:review_id>", ajax_delete_review, name="ajax_delete_review"),
    path("review/ajax/get/<int:review_id>", ajax_get_review, name="ajax_get_review"),
    path("review/ajax/list-my/", ajax_list_my_reviews, name="ajax_list_my_reviews"),
]
