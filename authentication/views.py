from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login as auth_login
from user_profile.models import CoachProfile, UserProfile, Certification
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
import json
import base64
import uuid

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
            
            try:
                coach_profile = CoachProfile.objects.get(user=user)
                user_type = "coach"
                is_coach = True
            except CoachProfile.DoesNotExist:
                user_type = "trainee"
                is_coach = False
            
            return JsonResponse({
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "user_type": user_type,
                "is_coach": is_coach,
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