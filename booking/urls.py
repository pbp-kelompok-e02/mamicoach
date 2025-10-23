from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # Booking confirmation & success pages
    path('confirm/<int:course_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('success/<int:booking_id>/', views.booking_success, name='booking_success'),
    
    # NEW API Endpoints (using CoachAvailability)
    path('api/course/<int:course_id>/start-times/', views.api_course_start_times, name='api_course_start_times'),
    path('api/course/<int:course_id>/create/', views.api_booking_create, name='api_booking_create'),
    path('api/bookings/', views.api_booking_list, name='api_booking_list'),
    path('api/booking/<int:booking_id>/status/', views.api_booking_update_status, name='api_booking_update_status'),
    path('api/booking/<int:booking_id>/cancel/', views.api_booking_cancel, name='api_booking_cancel'),
    path('api/booking/<int:booking_id>/mark-paid/', views.api_booking_mark_as_paid, name='api_booking_mark_as_paid'),
    
    # ✅ PERBAIKI: Ganti dari get_available_dates ke api_coach_available_dates_legacy
    path('api/coach/<int:coach_id>/available-dates/', views.api_coach_available_dates_legacy, name='api_coach_available_dates_legacy'),
    path('api/coach/<int:coach_id>/available-times/', views.api_coach_available_times_legacy, name='api_coach_available_times_legacy'),
]