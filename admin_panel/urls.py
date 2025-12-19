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
    
    # ==================== JSON API Endpoints for Flutter ====================
    # Authentication APIs (JWT)
    path('api/login/', views.api_admin_login, name='api_login'),
    path('api/logout/', views.api_admin_logout, name='api_logout'),
    path('api/refresh/', views.api_admin_refresh_token, name='api_refresh_token'),
    
    # Dashboard API
    path('api/dashboard/', views.api_dashboard_stats, name='api_dashboard'),
    
    # Users APIs
    path('api/users/', views.api_users_list, name='api_users_list'),
    path('api/users/<int:user_id>/', views.api_user_detail, name='api_user_detail'),
    path('api/users/<int:user_id>/delete/', views.api_user_delete, name='api_user_delete'),
    
    # Coaches APIs
    path('api/coaches/', views.api_coaches_list, name='api_coaches_list'),
    path('api/coaches/<int:coach_id>/', views.api_coach_detail, name='api_coach_detail'),
    path('api/coaches/<int:coach_id>/verify/', views.api_coach_verify, name='api_coach_verify'),
    path('api/coaches/<int:coach_id>/delete/', views.api_coach_delete, name='api_coach_delete'),
    
    # Courses APIs
    path('api/courses/', views.api_courses_list, name='api_courses_list'),
    path('api/courses/<int:course_id>/', views.api_course_detail, name='api_course_detail'),
    path('api/courses/<int:course_id>/delete/', views.api_course_delete, name='api_course_delete'),
    
    # Booking APIs
    path('api/bookings/', views.api_bookings_list, name='api_bookings_list'),
    path('api/bookings/<int:booking_id>/', views.api_booking_detail, name='api_booking_detail'),
    path('api/bookings/<int:booking_id>/update-status/', views.api_booking_update_status, name='api_booking_update_status'),
    path('api/bookings/<int:booking_id>/delete/', views.api_booking_delete, name='api_booking_delete'),
    
    # Payment APIs
    path('api/payments/', views.api_payments_list, name='api_payments_list'),
    path('api/payments/<int:payment_id>/', views.api_payment_detail, name='api_payment_detail'),
    path('api/payments/<int:payment_id>/update-status/', views.api_payment_update_status, name='api_payment_update_status'),
    
    # Activity Logs API
    path('api/logs/', views.api_activity_logs, name='api_logs'),
]
