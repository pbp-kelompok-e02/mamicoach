from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # OLD endpoints (keep for backward compatibility)
    path('api/coach/<int:coach_id>/available-dates/', views.get_available_dates, name='get_available_dates'),
    path('api/coach/<int:coach_id>/available-times/', views.get_available_times, name='get_available_times'),
    path('api/create/<int:course_id>/', views.create_booking, name='create_booking'),
    
    # NEW API endpoints for availability system
    path('api/course/<int:course_id>/start-times/', views.api_course_start_times, name='api_course_start_times'),
    path('api/course/<int:course_id>/create/', views.api_booking_create, name='api_booking_create'),
    path('api/bookings/', views.api_booking_list, name='api_booking_list'),
    path('api/booking/<int:booking_id>/status/', views.api_booking_update_status, name='api_booking_update_status'),
    path('api/booking/<int:booking_id>/mark-paid/', views.api_booking_mark_as_paid, name='api_booking_mark_paid'),
    path('api/booking/<int:booking_id>/cancel/', views.api_booking_cancel, name='api_booking_cancel'),
    
    # Page views
    path('confirm/<int:course_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('success/<int:booking_id>/', views.booking_success, name='booking_success'),
]