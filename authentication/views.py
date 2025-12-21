from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from user_profile.models import CoachProfile, UserProfile, Certification
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
import json
import base64
import uuid
import logging

from authentication.models import FcmDeviceToken

logger = logging.getLogger(__name__)

# Create your views here.
@csrf_exempt
def api_login(request):
    username = request.POST.get('username')
    password = request.POST.get('password')
    
    if not username or not password:
        return JsonResponse({
            "status": False,
            "message": "Username and password are required."
        }, status=400)
    
    user = authenticate(username=username, password=password)
    if user is not None:
        if user.is_active:
            auth_login(request, user)
            logger.info("api_login success user_id=%s username=%s", user.id, user.username)
            
            try:
                coach_profile = CoachProfile.objects.get(user=user)
                user_type = "coach"
                is_coach = True
                profile_image = coach_profile.image_url
            except CoachProfile.DoesNotExist:
                user_type = "trainee"
                is_coach = False
                try:
                    user_profile = UserProfile.objects.get(user=user)
                    profile_image = user_profile.image_url
                except UserProfile.DoesNotExist:
                     # Fallback if UserProfile doesn't exist (though it should)
                    profile_image = f'https://ui-avatars.com/api/?name={user.get_full_name() or user.username}&background=35A753&color=ffffff'
            
            return JsonResponse({
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_type": user_type,
                "is_coach": is_coach,
                "profile_image": profile_image,
                "status": True,
                "message": "Login successful!"
            }, status=200)
        else:
            return JsonResponse({
                "status": False,
                "message": "Login failed, account is disabled."
            }, status=401)

    else:
        return JsonResponse({
            "status": False,
            "message": "Login failed, please check your username or password."
        }, status=401)


@csrf_exempt
def api_register_user(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "status": False,
                "message": "Invalid JSON data."
            }, status=400)
        
        username = data.get('username', '').strip()
        password1 = data.get('password1', '')
        password2 = data.get('password2', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        if not username:
            return JsonResponse({
                "status": False,
                "message": "Username is required."
            }, status=400)
        
        if not first_name:
            return JsonResponse({
                "status": False,
                "message": "First name is required."
            }, status=400)
        
        if not last_name:
            return JsonResponse({
                "status": False,
                "message": "Last name is required."
            }, status=400)
        
        if not password1 or not password2:
            return JsonResponse({
                "status": False,
                "message": "Password is required."
            }, status=400)
        
        if len(password1) < 8:
            return JsonResponse({
                "status": False,
                "message": "Password must be at least 8 characters long."
            }, status=400)
        
        if password1 != password2:
            return JsonResponse({
                "status": False,
                "message": "Passwords do not match."
            }, status=400)
        
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                "status": False,
                "message": "Username already exists."
            }, status=400)
        
        user = User.objects.create_user(
            username=username,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        user.save()
        
        UserProfile.objects.create(user=user)
        
        return JsonResponse({
            "username": user.username,
            "status": True,
            "message": "User registered successfully!"
        }, status=200)
    
    else:
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=400)
    

@csrf_exempt
def api_register_coach(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                "status": False,
                "message": "Invalid JSON data."
            }, status=400)
        
        username = data.get('username', '').strip()
        password1 = data.get('password1', '')
        password2 = data.get('password2', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        bio = data.get('bio', '').strip()
        expertise = data.get('expertise', [])  # List of expertise areas
        certifications = data.get('certifications', [])
        profile_image_base64 = data.get('profile_image', '')  # Base64 string
        
        # Validate required fields
        if not username:
            return JsonResponse({
                "status": False,
                "message": "Username is required."
            }, status=400)
        
        if not first_name:
            return JsonResponse({
                "status": False,
                "message": "First name is required."
            }, status=400)
        
        if not last_name:
            return JsonResponse({
                "status": False,
                "message": "Last name is required."
            }, status=400)
        
        if not password1 or not password2:
            return JsonResponse({
                "status": False,
                "message": "Password is required."
            }, status=400)
        
        # Check password length
        if len(password1) < 8:
            return JsonResponse({
                "status": False,
                "message": "Password must be at least 8 characters long."
            }, status=400)
        
        # Check if the passwords match
        if password1 != password2:
            return JsonResponse({
                "status": False,
                "message": "Passwords do not match."
            }, status=400)
        
        # Check if bio is provided
        if not bio:
            return JsonResponse({
                "status": False,
                "message": "Bio is required for coach registration."
            }, status=400)
        
        # Check if expertise is provided
        if not expertise or not isinstance(expertise, list) or len(expertise) == 0:
            return JsonResponse({
                "status": False,
                "message": "At least one expertise area is required."
            }, status=400)
        
        # Check if the username is already taken
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                "status": False,
                "message": "Username already exists."
            }, status=400)
        
        # Create the new user
        user = User.objects.create_user(
            username=username,
            password=password1,
            first_name=first_name,
            last_name=last_name
        )
        user.save()
        
        # Create CoachProfile
        coach_profile = CoachProfile.objects.create(
            user=user,
            bio=bio,
            expertise=expertise
        )
        
        # Handle profile image if provided (base64)
        if profile_image_base64:
            try:
                # Remove header if present (e.g., "data:image/png;base64,")
                if ',' in profile_image_base64:
                    format, imgstr = profile_image_base64.split(';base64,')
                    ext = format.split('/')[-1].lower()
                else:
                    imgstr = profile_image_base64
                    ext = 'jpg'
                
                # Validate image format (only allow common image formats)
                allowed_formats = ['jpg', 'jpeg', 'png', 'gif', 'webp']
                if ext not in allowed_formats:
                    return JsonResponse({
                        "status": False,
                        "message": f"Invalid image format. Allowed formats: {', '.join(allowed_formats)}"
                    }, status=400)
                
                # Decode base64 string
                data = base64.b64decode(imgstr)
                
                # Validate file size (max 5MB)
                max_size = 5 * 1024 * 1024  # 5MB in bytes
                if len(data) > max_size:
                    return JsonResponse({
                        "status": False,
                        "message": "Image size too large. Maximum size is 5MB."
                    }, status=400)
                
                # Generate unique filename
                filename = f'coach_profile_{user.username}_{uuid.uuid4().hex[:8]}.{ext}'
                
                # Save image to profile
                coach_profile.profile_image.save(filename, ContentFile(data), save=True)
            except Exception as e:
                return JsonResponse({
                    "status": False,
                    "message": f"Failed to upload image: {str(e)}"
                }, status=400)
        
        if certifications and isinstance(certifications, list):
            for cert in certifications:
                if isinstance(cert, dict):
                    cert_name = cert.get('name', '').strip()
                    cert_url = cert.get('url', '').strip()
                    if cert_name and cert_url:
                        Certification.objects.create(
                            coach=coach_profile,
                            certificate_name=cert_name,
                            file_url=cert_url,
                            status='pending'
                        )
        
        return JsonResponse({
            "username": user.username,
            "status": True,
            "message": "Coach registered successfully!"
        }, status=200)
    
    else:
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=400)


@csrf_exempt
def api_logout(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "status": False,
            "message": "Not logged in."
        }, status=401)
    
    auth_logout(request)
    logger.info("api_logout user_id=%s", getattr(request.user, 'id', None))
    return JsonResponse({
        "status": True,
        "message": "Logout successful!"
    }, status=200)


@csrf_exempt
def api_fcm_token(request):
    """Register/update the current user's FCM token.

    Expects JSON: {"token": "...", "platform": "android"}
    Uses session authentication (pbp_django_auth cookies).
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({
            "status": False,
            "message": "Authentication required."
        }, status=401)

    data = None
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({
                "status": False,
                "message": "Invalid JSON data."
            }, status=400)
    else:
        # Support form-encoded (CookieRequest.post) for simpler client integration.
        data = request.POST

    token = (data.get('token') or '').strip()
    platform = (data.get('platform') or 'android').strip().lower()

    if not token:
        return JsonResponse({
            "status": False,
            "message": "Token is required."
        }, status=400)

    if platform not in ("android",):
        # Keeping scope Android-only per your request.
        platform = "android"

    print(
        f"[FCM] register user_id={request.user.id} platform={platform} token_prefix={token[:12]}"
    )

    logger.info(
        "api_fcm_token register user_id=%s platform=%s token_prefix=%s",
        request.user.id,
        platform,
        token[:12],
    )

    # Ensure a token belongs to exactly one user.
    existing = FcmDeviceToken.objects.filter(token=token).first()
    if existing is not None and existing.user_id != request.user.id:
        existing.user = request.user
        existing.platform = platform
        existing.save(update_fields=["user", "platform", "updated_at"])
    else:
        FcmDeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": request.user,
                "platform": platform,
            },
        )

    return JsonResponse({
        "status": True,
        "message": "FCM token registered."
    }, status=200)


@csrf_exempt
def api_fcm_token_delete(request):
    """Unregister/delete the current user's FCM token.

    Expects POST with either:
      - token: the device token to delete (preferred)
      - OR delete_all=true to delete all android tokens for this user

    Supports JSON or form-encoded bodies.
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({
            "status": False,
            "message": "Authentication required."
        }, status=401)

    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({
                "status": False,
                "message": "Invalid JSON data."
            }, status=400)
    else:
        data = request.POST

    token = (data.get('token') or '').strip()
    platform = (data.get('platform') or 'android').strip().lower()
    delete_all_raw = (data.get('delete_all') or '').strip().lower()
    delete_all = delete_all_raw in ('1', 'true', 'yes', 'y')

    if platform not in ("android",):
        platform = "android"

    if not token and not delete_all:
        return JsonResponse({
            "status": False,
            "message": "Token is required unless delete_all=true."
        }, status=400)

    qs = FcmDeviceToken.objects.filter(user=request.user, platform=platform)
    if token:
        qs = qs.filter(token=token)

    deleted_count, _ = qs.delete()
    logger.info(
        "api_fcm_token_delete user_id=%s platform=%s token_prefix=%s delete_all=%s deleted=%s",
        request.user.id,
        platform,
        token[:12] if token else None,
        delete_all,
        deleted_count,
    )

    return JsonResponse({
        "status": True,
        "deleted": deleted_count,
        "message": "FCM token unregistered."
    }, status=200)


@csrf_exempt
def api_fcm_tokens_me(request):
    """Debug endpoint to list current user's registered FCM tokens (prefix only)."""
    if request.method != 'GET':
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({
            "status": False,
            "message": "Authentication required."
        }, status=401)

    tokens = list(
        FcmDeviceToken.objects.filter(user=request.user, platform="android")
        .values_list("token", flat=True)
        .distinct()
    )

    print(f"[FCM] tokens_me user_id={request.user.id} token_count={len(tokens)}")

    return JsonResponse({
        "status": True,
        "tokens": [t[:12] for t in tokens],
        "count": len(tokens),
    }, status=200)


@csrf_exempt
def api_test_push(request):
    """Send a test push notification to the current user (Android only).

    Useful for local debugging: confirms service account, token storage, and delivery.
    """
    if request.method != 'POST':
        return JsonResponse({
            "status": False,
            "message": "Invalid request method."
        }, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({
            "status": False,
            "message": "Authentication required."
        }, status=401)

    data = {}
    if request.content_type and "application/json" in request.content_type:
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            data = {}
    else:
        # Support form-encoded.
        data = request.POST

    title = (data.get('title') or 'MamiCoach test push').strip()
    body = (data.get('body') or 'If you see this, FCM is working.').strip()

    tokens = list(
        FcmDeviceToken.objects.filter(user=request.user, platform="android")
        .values_list("token", flat=True)
        .distinct()
    )

    logger.info(
        "api_test_push user_id=%s token_count=%s",
        request.user.id,
        len(tokens),
    )

    print(f"[FCM] test_push user_id={request.user.id} token_count={len(tokens)}")

    if not tokens:
        return JsonResponse({
            "status": False,
            "message": "No FCM tokens registered for this user yet.",
        }, status=400)

    try:
        from mami_coach.fcm import send_push_to_tokens

        result = send_push_to_tokens(
            tokens,
            title=title,
            body=body,
            data={"type": "test"},
        )

        print(
            f"[FCM] test_push result user_id={request.user.id} success={result.get('success')} failure={result.get('failure')}"
        )
        logger.info(
            "api_test_push result user_id=%s success=%s failure=%s",
            request.user.id,
            result.get("success"),
            result.get("failure"),
        )
        return JsonResponse({
            "status": True,
            "result": result,
        }, status=200)
    except Exception:
        logger.exception("api_test_push failed user_id=%s", request.user.id)
        return JsonResponse({
            "status": False,
            "message": "Failed to send push (check server logs).",
        }, status=500)