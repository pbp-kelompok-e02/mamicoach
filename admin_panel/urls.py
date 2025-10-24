from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    # Authentication
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    path('change-password/', views.change_password, name='change_password'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Module Management
    path('users/', views.users_management, name='users'),
    path('coaches/', views.coaches_management, name='coaches'),
    path('courses/', views.courses_management, name='courses'),
    path('bookings/', views.bookings_management, name='bookings'),
    path('payments/', views.payments_management, name='payments'),
    
    # Settings
    path('settings/', views.settings_management, name='settings'),
    
    # Activity Logs
    path('logs/', views.activity_logs, name='logs'),
    
    # CRUD Operations
    path('coach/<int:coach_id>/verify/', views.coach_verify, name='coach_verify'),
    path('coach/<int:coach_id>/verification/', views.coach_verification_detail, name='coach_verification_detail'),
    path('coach/<int:coach_id>/delete/', views.coach_delete, name='coach_delete'),
    path('user/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('course/<int:course_id>/delete/', views.course_delete, name='course_delete'),
    path('booking/<int:booking_id>/update-status/', views.booking_update_status, name='booking_update_status'),
    path('booking/<int:booking_id>/delete/', views.booking_delete, name='booking_delete'),
    path('payment/<int:payment_id>/update-status/', views.payment_update_status, name='payment_update_status'),
]
