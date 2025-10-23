from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # Halaman detail course dengan tombol "Jadwalkan Sesi"
    # path('course/<int:course_id>/', views.course_detail, name='course_detail'),
    
    # AJAX endpoints untuk kalender booking
    path('api/coach/<int:coach_id>/available-dates/', views.get_available_dates, name='get_available_dates'),
    path('api/coach/<int:coach_id>/available-times/', views.get_available_times, name='get_available_times'),
    
    # Create booking (setelah user pilih waktu)
    path('api/create/<int:course_id>/', views.create_booking, name='create_booking'),
]