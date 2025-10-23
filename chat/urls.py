from django.urls import path

from .views import (
    chat_index, chat_detail, get_chat_sessions, 
    get_messages, send_message, mark_messages_read, create_chat_with_coach,
    upload_attachment
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
    path("chat/api/<uuid:session_id>/upload/", upload_attachment, name="upload_attachment"),
]

