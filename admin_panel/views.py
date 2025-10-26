"""
Admin panel views for managing the MamiCoach platform
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Sum
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from functools import wraps

from booking.models import Booking
from payment.models import Payment
from courses_and_coach.models import Course
from user_profile.models import CoachProfile, UserProfile, AdminVerification
from .models import AdminSettings, AdminActivityLog, AdminUser


def admin_login_required(view_func):
    """Custom decorator to check if admin is logged in"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'admin_user_id' not in request.session:
            return redirect('admin_panel:login')
        
        try:
            admin_user = AdminUser.objects.get(id=request.session['admin_user_id'], is_active=True)
            request.admin_user = admin_user
        except AdminUser.DoesNotExist:
            del request.session['admin_user_id']
            return redirect('admin_panel:login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def log_admin_activity(admin_user, action, module, description, request=None):
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
        admin_user=admin_user,
        action=action,
        module=module,
        description=description,
        ip_address=ip_address,
        user_agent=user_agent
    )


@require_http_methods(["GET", "POST"])
def admin_login(request):
    """Admin login page"""
    # Check if already logged in
    if 'admin_user_id' in request.session:
        return redirect('admin_panel:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            admin_user = AdminUser.objects.get(username=username, is_active=True)
            if admin_user.check_password(password):
                # Set session
                request.session['admin_user_id'] = admin_user.id
                admin_user.last_login = timezone.now()
                admin_user.save()
                
                log_admin_activity(admin_user, 'login', 'auth', f'Admin logged in', request)
                messages.success(request, f'Welcome back, {admin_user.username}!')
                return redirect('admin_panel:dashboard')
            else:
                messages.error(request, 'Invalid credentials')
        except AdminUser.DoesNotExist:
            messages.error(request, 'Invalid credentials')
    
    return render(request, 'admin_panel/login.html')


@admin_login_required
def admin_logout(request):
    """Admin logout"""
    log_admin_activity(request.admin_user, 'logout', 'auth', f'Admin logged out', request)
    request.session.flush()
    messages.success(request, 'You have been logged out successfully')
    return redirect('admin_panel:login')


@admin_login_required
def dashboard(request):
    """Main admin dashboard"""
    # Get statistics
    total_users = UserProfile.objects.count()
    total_coaches = CoachProfile.objects.count()
    total_courses = Course.objects.count()
    total_bookings = Booking.objects.count()
    
    # Bookings by status
    pending_bookings = Booking.objects.filter(status='pending').count()
    confirmed_bookings = Booking.objects.filter(status='confirmed').count()
    done_bookings = Booking.objects.filter(status='done').count()
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related('user', 'course').order_by('-created_at')[:10]
    
    # Payment statistics
    total_revenue = Payment.objects.filter(status__in=['settlement', 'capture']).aggregate(
        total=Sum('amount')
    )['total'] or 0
    
    # Recent activity logs
    recent_logs = AdminActivityLog.objects.select_related('admin_user').order_by('-timestamp')[:10]
    
    log_admin_activity(request.admin_user, 'view', 'dashboard', 'Viewed admin dashboard', request)
    
    context = {
        'user': request.admin_user,
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


@admin_login_required
def users_management(request):
    """User management page"""
    users = UserProfile.objects.select_related('user').order_by('-user__date_joined')
    
    log_admin_activity(request.admin_user, 'view', 'users', 'Viewed users management', request)
    
    context = {
        'user': request.admin_user,
        'users': users,
    }
    
    return render(request, 'admin_panel/users.html', context)


@admin_login_required
def coaches_management(request):
    """Coach management page"""
    coaches = CoachProfile.objects.select_related('user').prefetch_related('adminverification').order_by('-id')
    
    log_admin_activity(request.admin_user, 'view', 'coaches', 'Viewed coaches management', request)
    
    context = {
        'user': request.admin_user,
        'coaches': coaches,
    }
    
    return render(request, 'admin_panel/coaches.html', context)


@admin_login_required
def courses_management(request):
    """Course management page"""
    courses = Course.objects.select_related('coach').order_by('-id')
    
    log_admin_activity(request.admin_user, 'view', 'courses', 'Viewed courses management', request)
    
    context = {
        'user': request.admin_user,
        'courses': courses,
    }
    
    return render(request, 'admin_panel/courses.html', context)


@admin_login_required
def bookings_management(request):
    """Booking management page"""
    bookings = Booking.objects.select_related('user', 'course').order_by('-created_at')
    
    log_admin_activity(request.admin_user, 'view', 'bookings', 'Viewed bookings management', request)
    
    context = {
        'user': request.admin_user,
        'bookings': bookings,
    }
    
    return render(request, 'admin_panel/bookings.html', context)


@admin_login_required
def payments_management(request):
    """Payment management page"""
    payments = Payment.objects.select_related('booking__user', 'booking__course').order_by('-created_at')
    
    log_admin_activity(request.admin_user, 'view', 'payments', 'Viewed payments management', request)
    
    context = {
        'user': request.admin_user,
        'payments': payments,
    }
    
    return render(request, 'admin_panel/payments.html', context)


@admin_login_required
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
                updated_by=request.admin_user
            )
            log_admin_activity(request.admin_user, 'create', 'settings', f'Added setting {key}', request)
            messages.success(request, f'Setting {key} added successfully')
            
        elif action == 'update':
            setting_id = request.POST.get('setting_id')
            setting = get_object_or_404(AdminSettings, id=setting_id)
            old_value = setting.value
            setting.value = request.POST.get('value')
            setting.updated_by = request.admin_user
            setting.save()
            
            log_admin_activity(request.admin_user, 'update', 'settings', f'Updated {setting.key} from "{old_value}" to "{setting.value}"', request)
            messages.success(request, f'Setting {setting.key} updated successfully')
            
        elif action == 'delete':
            setting_id = request.POST.get('setting_id')
            setting = get_object_or_404(AdminSettings, id=setting_id)
            key = setting.key
            setting.delete()
            
            log_admin_activity(request.admin_user, 'delete', 'settings', f'Deleted setting {key}', request)
            messages.success(request, f'Setting {key} deleted successfully')
        
        return redirect('admin_panel:settings')
    
    # GET request - display settings
    settings = AdminSettings.objects.all().order_by('module', 'key')
    
    log_admin_activity(request.admin_user, 'view', 'settings', 'Viewed settings management', request)
    
    context = {
        'user': request.admin_user,
        'settings': settings,
    }
    
    return render(request, 'admin_panel/settings.html', context)


@admin_login_required
def activity_logs(request):
    """Activity logs page"""
    action_filter = request.GET.get('action', 'all')
    
    if action_filter != 'all':
        logs = AdminActivityLog.objects.filter(action=action_filter).select_related('admin_user').order_by('-timestamp')[:500]
    else:
        logs = AdminActivityLog.objects.select_related('admin_user').order_by('-timestamp')[:500]
    
    context = {
        'user': request.admin_user,
        'logs': logs,
    }
    
    return render(request, 'admin_panel/logs.html', context)


@admin_login_required
def change_password(request):
    """Change admin password"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        # Verify current password
        if not request.admin_user.check_password(old_password):
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
        request.admin_user.set_password(new_password1)
        request.admin_user.save()
        
        log_admin_activity(request.admin_user, 'update', 'auth', 'Changed admin password', request)
        
        messages.success(request, 'Password changed successfully. Please login again.')
        return redirect('admin_panel:logout')
    
    context = {
        'user': request.admin_user,
    }
    return render(request, 'admin_panel/change_password.html', context)


# ==================== CRUD Operations ====================

@admin_login_required
def coach_verify(request, coach_id):
    """Toggle coach verified badge (independent from approval status)"""
    coach = get_object_or_404(CoachProfile, id=coach_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'verify':
            # Just toggle the verified badge - doesn't affect approval status
            coach.verified = True
            coach.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Added verified badge to coach {coach.user.username}', request)
            messages.success(request, f'Verified badge added to coach {coach.user.username}!')
            
        elif action == 'unverify':
            # Remove verified badge - doesn't affect approval status
            coach.verified = False
            coach.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Removed verified badge from coach {coach.user.username}', request)
            messages.success(request, f'Verified badge removed from coach {coach.user.username}.')
    
    return redirect('admin_panel:coaches')


@admin_login_required
def coach_verification_detail(request, coach_id):
    """View and manage coach approval status (ability to train on platform)"""
    coach = get_object_or_404(CoachProfile, id=coach_id)
    
    admin_verification, created = AdminVerification.objects.get_or_create(
        coach=coach,
        defaults={'certificate_url': '', 'status': 'pending'}
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('notes', '')
        
        if action == 'approve':
            # Approve = Set status to approved AND give verified badge
            admin_verification.status = 'approved'
            admin_verification.notes = notes or f'Approved by {request.admin_user.username}'
            admin_verification.save()
            
            coach.verified = True
            coach.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Approved coach {coach.user.username} - verified badge granted', request)
            messages.success(request, f'Coach {coach.user.username} has been approved and verified badge granted!')
            
        elif action == 'reject':
            # Reject = Set status to rejected AND remove verified badge
            admin_verification.status = 'rejected'
            admin_verification.notes = notes or f'Rejected by {request.admin_user.username}'
            admin_verification.save()
            
            coach.verified = False
            coach.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Rejected coach {coach.user.username} - verified badge removed', request)
            messages.warning(request, f'Coach {coach.user.username} has been rejected and verified badge removed.')
            
        elif action == 'pending':
            # Set to pending review
            admin_verification.status = 'pending'
            admin_verification.notes = notes
            admin_verification.save()
            
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Set approval status to pending for coach {coach.user.username}', request)
            messages.info(request, f'Coach {coach.user.username} approval status set to pending.')
        
        elif action == 'toggle_verified':
            # Toggle verified badge independently
            coach.verified = not coach.verified
            coach.save()
            
            badge_action = 'added' if coach.verified else 'removed'
            log_admin_activity(request.admin_user, 'update', 'coaches', 
                             f'Verified badge {badge_action} for coach {coach.user.username}', request)
            messages.success(request, f'Verified badge {badge_action} for coach {coach.user.username}!')
        
        return redirect('admin_panel:coach_verification_detail', coach_id=coach_id)
    
    context = {
        'user': request.admin_user,
        'coach': coach,
        'admin_verification': admin_verification,
    }
    return render(request, 'admin_panel/coach_verification_detail.html', context)


@admin_login_required
def coach_delete(request, coach_id):
    """Delete a coach"""
    coach = get_object_or_404(CoachProfile, id=coach_id)
    
    if request.method == 'POST':
        username = coach.user.username
        user = coach.user
        coach.delete()
        user.delete()  # Also delete the associated user account
        
        log_admin_activity(request.admin_user, 'delete', 'coaches', f'Deleted coach {username}', request)
        messages.success(request, f'Coach {username} has been deleted successfully!')
        return redirect('admin_panel:coaches')
    
    context = {
        'user': request.admin_user,
        'coach': coach,
    }
    return render(request, 'admin_panel/coach_delete_confirm.html', context)


@admin_login_required
def user_delete(request, user_id):
    """Delete a user"""
    from django.contrib.auth.models import User
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        username = user_obj.username
        user_obj.delete()
        
        log_admin_activity(request.admin_user, 'delete', 'users', f'Deleted user {username}', request)
        messages.success(request, f'User {username} has been deleted successfully!')
        return redirect('admin_panel:users')
    
    context = {
        'user': request.admin_user,
        'user_obj': user_obj,
    }
    return render(request, 'admin_panel/user_delete_confirm.html', context)


@admin_login_required
def course_delete(request, course_id):
    """Delete a course"""
    course = get_object_or_404(Course, id=course_id)
    
    if request.method == 'POST':
        course_name = course.title
        course.delete()
        
        log_admin_activity(request.admin_user, 'delete', 'courses', f'Deleted course {course_name}', request)
        messages.success(request, f'Course "{course_name}" has been deleted successfully!')
        return redirect('admin_panel:courses')
    
    context = {
        'user': request.admin_user,
        'course': course,
    }
    return render(request, 'admin_panel/course_delete_confirm.html', context)


@admin_login_required
def booking_update_status(request, booking_id):
    """Update booking status"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = booking.status
        
        if new_status in dict(Booking.STATUS_CHOICES):
            booking.status = new_status
            booking.save()
            
            log_admin_activity(request.admin_user, 'update', 'bookings', 
                             f'Updated booking #{booking.id} status from {old_status} to {new_status}', request)
            messages.success(request, f'Booking status updated to {new_status}!')
        else:
            messages.error(request, 'Invalid status!')
    
    return redirect('admin_panel:bookings')


@admin_login_required
def booking_delete(request, booking_id):
    """Delete a booking"""
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == 'POST':
        booking_info = f"#{booking.id} - {booking.user.username} - {booking.course.title}"
        booking.delete()
        
        log_admin_activity(request.admin_user, 'delete', 'bookings', f'Deleted booking {booking_info}', request)
        messages.success(request, f'Booking has been deleted successfully!')
        return redirect('admin_panel:bookings')
    
    context = {
        'user': request.admin_user,
        'booking': booking,
    }
    return render(request, 'admin_panel/booking_delete_confirm.html', context)


@admin_login_required
def payment_update_status(request, payment_id):
    """Update payment status"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = payment.status
        
        payment.status = new_status
        payment.save()
        
        log_admin_activity(request.admin_user, 'update', 'payments', 
                         f'Updated payment {payment.order_id} status from {old_status} to {new_status}', request)
        messages.success(request, f'Payment status updated to {new_status}!')
    
    return redirect('admin_panel:payments')
