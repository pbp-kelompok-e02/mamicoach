from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST
import json
from .models import ChatSession, ChatMessage
from user_profile.models import CoachProfile

# Create your views here.
@login_required(login_url="/login")
def chat_index(request):
    """Main chat page showing all chat sessions"""
    return render(request, "pages/chat_interface.html")

@login_required(login_url="/login")
def chat_detail(request, session_id):
    """Individual chat session page"""
    session = get_object_or_404(ChatSession, id=session_id)
    
    # Check if user is part of this chat session
    if not _user_in_session(request.user, session):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    context = {
        'selected_session': session,
        'selected_session_id': str(session_id),
        'other_user': session.get_other_user(request.user)
    }
    return render(request, "pages/chat_interface.html", context)

@login_required(login_url="/login")
def get_chat_sessions(request):
    """AJAX endpoint to get all chat sessions for current user"""
    # Check if the current user is a coach by checking their coach profile
    is_coach = CoachProfile.objects.filter(user=request.user).exists()
    
    if is_coach:
        # If user is a coach, show sessions where they are the coach
        sessions = ChatSession.objects.filter(
            coach=request.user
        ).order_by('-started_at')
    else:
        # If user is not a coach, show sessions where they are the user
        sessions = ChatSession.objects.filter(
            user=request.user
        ).order_by('-started_at')
    
    sessions_data = []
    # Sort sessions by last message timestamp
    sessions_with_messages = []
    for session in sessions:
        other_user = session.get_other_user(request.user)
        last_message = ChatMessage.objects.filter(session=session).order_by('-timestamp').first()
        
        # Count unread messages from the other user
        unread_count = ChatMessage.objects.filter(
            session=session,
            read=False, 
            sender=other_user
        ).count()
        
        sessions_with_messages.append({
            'session': session,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': unread_count,
            'last_message_time': last_message.timestamp if last_message else session.started_at
        })
    
    # Sort by last message timestamp (most recent first)
    sessions_with_messages.sort(key=lambda x: x['last_message_time'], reverse=True)
    
    # Build the response data
    for item in sessions_with_messages:
        session = item['session']
        other_user = item['other_user']
        last_message = item['last_message']
        unread_count = item['unread_count']
        
        sessions_data.append({
            'id': str(session.id),
            'other_user': _serialize_user(other_user),
            'last_message': {
                'content': last_message.content if last_message else '',
                'timestamp': last_message.timestamp.isoformat() if last_message else session.started_at.isoformat(),
                'is_read': last_message.read if last_message else True,
                'sender_is_me': last_message.sender == request.user if last_message else False
            },
            'unread_count': unread_count
        })
    
    return JsonResponse({'sessions': sessions_data})

@login_required(login_url="/login")
def get_messages(request, session_id):
    """AJAX endpoint to get messages for a specific chat session"""
    session = get_object_or_404(ChatSession, id=session_id)
    
    # Check if user is part of this chat session
    if not _user_in_session(request.user, session):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
    messages_data = [
        _serialize_message(message, is_current_user=message.sender == request.user)
        for message in messages
    ]
    
    # Mark messages as read if they're from the other user
    unread_messages = ChatMessage.objects.filter(
        session=session,
        read=False
    ).exclude(sender=request.user)
    unread_messages.update(read=True)
    
    return JsonResponse({
        'messages': messages_data,
        'current_user_id': request.user.id
    })

@require_POST
@login_required(login_url="/login")
def send_message(request):
    """AJAX endpoint to send a new message"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        content = data.get('content', '').strip()
        
        if not session_id:
            return JsonResponse({'error': 'Session ID is required'}, status=400)
            
        if not content:
            return JsonResponse({'error': 'Message content cannot be empty'}, status=400)
        
        # Sanitize the message content
        content = strip_tags(content)
        
        # Verify content is not empty after sanitization
        if not content:
            return JsonResponse({'error': 'Message content cannot be empty'}, status=400)
        
        session = get_object_or_404(ChatSession, id=session_id)
        
        # Check if user is part of this chat session
        if not _user_in_session(request.user, session):
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Create new message
        message = ChatMessage.objects.create(
            session=session,
            sender=request.user,
            content=content
        )
        
        # Update session's last activity timestamp
        session.started_at = timezone.now()
        session.save(update_fields=['started_at'])
        
        return JsonResponse({
            'success': True,
            'message': _serialize_message(message, is_current_user=True)
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@login_required(login_url="/login")
def mark_messages_read(request):
    """AJAX endpoint to mark messages as read"""
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        
        if not session_id:
            return JsonResponse({'error': 'Session ID is required'}, status=400)
        
        session = get_object_or_404(ChatSession, id=session_id)
        
        # Check if user is part of this chat session
        if not _user_in_session(request.user, session):
            return JsonResponse({'error': 'Unauthorized'}, status=403)
        
        # Mark all unread messages from the other user as read
        unread_messages = ChatMessage.objects.filter(
            session=session, 
            read=False
        ).exclude(sender=request.user)
        updated_count = unread_messages.update(read=True)
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_POST
@login_required(login_url="/login")
def create_chat_with_coach(request, coach_id):
    """AJAX endpoint to create a chat session with a coach"""
    try:
        from django.contrib.auth.models import User
        
        # Get the coach user
        coach = get_object_or_404(User, id=coach_id)
        
        # Verify that the coach has a coach profile
        if not CoachProfile.objects.filter(user=coach).exists():
            return JsonResponse({'error': 'User is not a coach'}, status=400)
        
        # Prevent user from creating chat with themselves
        if request.user == coach:
            return JsonResponse({'error': 'Cannot create chat with yourself'}, status=400)
        
        # Check if chat session already exists
        existing_session = ChatSession.objects.filter(
            user=request.user,
            coach=coach
        ).first()
        
        if existing_session:
            # Return existing session
            return JsonResponse({
                'success': True,
                'session_id': str(existing_session.id),
                'message': 'Chat session already exists'
            })
        
        # Create new chat session
        session = ChatSession.objects.create(
            user=request.user,
            coach=coach
        )
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.id),
            'message': 'Chat session created successfully'
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# Helper functions
def _user_in_session(user, session):
    """Check if user is authorized to access this chat session"""
    return user == session.user or user == session.coach


def _serialize_message(message, is_current_user=None):
    """Serialize a ChatMessage object to dictionary"""
    return {
        'id': message.pk,
        'content': message.content,
        'timestamp': message.timestamp.isoformat(),
        'sender': {
            'username': message.sender.username,
            'first_name': message.sender.first_name,
            'last_name': message.sender.last_name,
        },
        'is_sent_by_me': is_current_user if is_current_user is not None else False,
        'read': message.read
    }


def _serialize_user(user):
    """Serialize a User object for chat purposes"""
    return {
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }
