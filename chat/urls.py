from django.urls import path

from .views import (
    chat_index, chat_detail, get_chat_sessions, 
    get_messages, send_message, mark_messages_read
)

app_name = "chat"

urlpatterns = [
    path("chat/", chat_index, name="chat_index"),
    path("chat/<uuid:session_id>/", chat_detail, name="chat_detail"),
    
    # AJAX endpoints
    path("api/chat/sessions/", get_chat_sessions, name="get_chat_sessions"),
    path("api/chat/<uuid:session_id>/messages/", get_messages, name="get_messages"),
    path("api/chat/send/", send_message, name="send_message"),
    path("api/chat/mark-read/", mark_messages_read, name="mark_messages_read"),
]
