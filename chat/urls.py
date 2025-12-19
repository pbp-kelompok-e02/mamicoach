from django.urls import path

from .views import (
    chat_index, chat_detail, get_chat_sessions, 
    get_messages, send_message, mark_messages_read, create_chat_with_coach,
    create_chat_with_user,
    upload_attachment, create_attachment, presend_booking, presend_course
)

app_name = "chat"

urlpatterns = [
    path("chat/", chat_index, name="chat_index"),
    path("chat/<uuid:session_id>/", chat_detail, name="chat_detail"),
    
    # AJAX endpoints
    path("chat/api/sessions/", get_chat_sessions, name="get_chat_sessions"),
    path("chat/api/<uuid:session_id>/messages/", get_messages, name="get_messages"),
    path("chat/api/send/", send_message, name="send_message"),
    path("chat/api/mark-read/", mark_messages_read, name="mark_messages_read"),
    path("chat/api/create-chat-with-coach/<int:coach_id>/", create_chat_with_coach, name="create_chat_with_coach"),
    path("chat/api/create-chat-with-user/<int:user_id>/", create_chat_with_user, name="create_chat_with_user"),
    path("chat/api/<uuid:session_id>/upload/", upload_attachment, name="upload_attachment"),
    path("chat/api/<uuid:session_id>/create-attachment/", create_attachment, name="create_attachment"),
    
    # Presend endpoints for booking and course embeds
    path("chat/presend-booking/<int:booking_id>/", presend_booking, name="presend_booking"),
    path("chat/presend-course/<int:course_id>/", presend_course, name="presend_course"),
]

