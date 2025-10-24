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
]
