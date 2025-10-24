"""
Admin panel views for managing the MamiCoach platform
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum
from django.views.decorators.http import require_http_methods

from booking.models import Booking
from payment.models import Payment
from courses_and_coach.models import Course
from user_profile.models import CoachProfile, UserProfile
from .models import AdminSettings, AdminActivityLog


def is_superuser(user):
    """Check if user is superuser"""
    return user.is_superuser


def log_admin_activity(user, action, module, description, request=None):
    """Helper function to log admin activities"""
    ip_address = None
    user_agent = ''
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AdminActivityLog.objects.create(
        user=user,
        action=action,
        module=module,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent
    )


@require_http_methods(["GET", "POST"])
def admin_login(request):
    """Admin login page"""
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            log_admin_activity(user, 'login', 'auth', f'Admin logged in', request)
            messages.success(request, f'Welcome back, {user.username}!')
            return redirect('admin_panel:dashboard')
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions')
    
    return render(request, 'admin_panel/login.html')


@login_required
@user_passes_test(is_superuser)
def admin_logout(request):
    """Admin logout"""
    log_admin_activity(request.user, 'logout', 'auth', f'Admin logged out', request)
    logout(request)
    messages.success(request, 'You have been logged out successfully')
    return redirect('admin_panel:login')


@login_required
@user_passes_test(is_superuser)
def dashboard(request):
    """Main admin dashboard"""
    # Get statistics
    total_users = User.objects.filter(is_superuser=False).count()
    total_coaches = CoachProfile.objects.count()
    total_courses = Course.objects.count()
    total_bookings = Booking.objects.count()
    
    # Bookings by status
    pending_bookings = Booking.objects.filter(status='pending').count()
    confirmed_bookings = Booking.objects.filter(status='confirmed').count()
    done_bookings = Booking.objects.filter(status='done').count()
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related('user_profile__user', 'course').order_by('-created_at')[:10]
    
    # Payment statistics
    total_revenue = Payment.objects.filter(status__in=['settlement', 'capture']).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Recent activity logs
    recent_logs = AdminActivityLog.objects.select_related('user').order_by('-timestamp')[:10]
    
    log_admin_activity(request.user, 'view', 'dashboard', 'Viewed admin dashboard', request)
    
    context = {
        'total_users': total_users,
        'total_coaches': total_coaches,
        'total_courses': total_courses,
        'total_bookings': total_bookings,
        'pending_bookings': pending_bookings,
        'confirmed_bookings': confirmed_bookings,
        'done_bookings': done_bookings,
        'total_revenue': total_revenue,
        'recent_bookings': recent_bookings,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'admin_panel/dashboard.html', context)


@login_required
@user_passes_test(is_superuser)
def users_management(request):
    """User management page"""
    users = User.objects.filter(is_superuser=False).select_related('userprofile').order_by('-date_joined')
    
    log_admin_activity(request.user, 'view', 'users', 'Viewed users management', request)
    
    context = {
        'users': users,
    }
    
    return render(request, 'admin_panel/users.html', context)


@login_required
@user_passes_test(is_superuser)
def coaches_management(request):
    """Coach management page"""
    coaches = CoachProfile.objects.all().order_by('-id')
    
    log_admin_activity(request.user, 'view', 'coaches', 'Viewed coaches management', request)
    
    context = {
        'coaches': coaches,
    }
    
    return render(request, 'admin_panel/coaches.html', context)


@login_required
@user_passes_test(is_superuser)
def courses_management(request):
    """Course management page"""
    courses = Course.objects.select_related('coach').order_by('-id')
    
    log_admin_activity(request.user, 'view', 'courses', 'Viewed courses management', request)
    
    context = {
        'courses': courses,
    }
    
    return render(request, 'admin_panel/courses.html', context)


@login_required
@user_passes_test(is_superuser)
def bookings_management(request):
    """Booking management page"""
    bookings = Booking.objects.select_related('user_profile__user', 'course').order_by('-created_at')
    
    log_admin_activity(request.user, 'view', 'bookings', 'Viewed bookings management', request)
    
    context = {
        'bookings': bookings,
    }
    
    return render(request, 'admin_panel/bookings.html', context)


@login_required
@user_passes_test(is_superuser)
def payments_management(request):
    """Payment management page"""
    payments = Payment.objects.select_related('booking__user_profile__user', 'booking__course').order_by('-created_at')
    
    log_admin_activity(request.user, 'view', 'payments', 'Viewed payments management', request)
    
    context = {
        'payments': payments,
    }
    
    return render(request, 'admin_panel/payments.html', context)


@login_required
@user_passes_test(is_superuser)
def settings_management(request):
    """Settings management page"""
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add':
            module = request.POST.get('module')
            key = request.POST.get('key')
            value = request.POST.get('value')
            
            AdminSettings.objects.create(
                module=module,
                key=key,
                value=value,
                updated_by=request.user
            )
            log_admin_activity(request.user, 'create', 'settings', f'Added setting {key}', request)
            messages.success(request, f'Setting {key} added successfully')
            
        elif action == 'update':
            setting_id = request.POST.get('setting_id')
            setting = get_object_or_404(AdminSettings, id=setting_id)
            old_value = setting.value
            setting.value = request.POST.get('value')
            setting.updated_by = request.user
            setting.save()
            
            log_admin_activity(request.user, 'update', 'settings', f'Updated {setting.key} from "{old_value}" to "{setting.value}"', request)
            messages.success(request, f'Setting {setting.key} updated successfully')
            
        elif action == 'delete':
            setting_id = request.POST.get('setting_id')
            setting = get_object_or_404(AdminSettings, id=setting_id)
            key = setting.key
            setting.delete()
            
            log_admin_activity(request.user, 'delete', 'settings', f'Deleted setting {key}', request)
            messages.success(request, f'Setting {key} deleted successfully')
        
        return redirect('admin_panel:settings')
    
    # GET request - display settings
    settings = AdminSettings.objects.all().order_by('module', 'key')
    
    log_admin_activity(request.user, 'view', 'settings', 'Viewed settings management', request)
    
    context = {
        'settings': settings,
    }
    
    return render(request, 'admin_panel/settings.html', context)


@login_required
@user_passes_test(is_superuser)
def activity_logs(request):
    """Activity logs page"""
    action_filter = request.GET.get('action', 'all')
    
    if action_filter != 'all':
        logs = AdminActivityLog.objects.filter(action=action_filter).select_related('user').order_by('-timestamp')[:500]
    else:
        logs = AdminActivityLog.objects.select_related('user').order_by('-timestamp')[:500]
    
    context = {
        'logs': logs,
    }
    
    return render(request, 'admin_panel/logs.html', context)


@login_required
@user_passes_test(is_superuser)
def change_password(request):
    """Change admin password"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Verify current password
        if not request.user.check_password(old_password):
            messages.error(request, 'Current password is incorrect')
            return redirect('admin_panel:change_password')
        
        # Verify new passwords match
        if new_password1 != new_password2:
            messages.error(request, 'New passwords do not match')
            return redirect('admin_panel:change_password')
        
        # Check password strength
        if len(new_password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long')
            return redirect('admin_panel:change_password')
        
        # Update password
        request.user.set_password(new_password1)
        request.user.save()
        
        log_admin_activity(request.user, 'update', 'auth', 'Changed admin password', request)
        
        messages.success(request, 'Password changed successfully. Please login again.')
        return redirect('admin_panel:logout')
    
    return render(request, 'admin_panel/change_password.html')
