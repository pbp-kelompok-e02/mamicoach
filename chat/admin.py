from django.contrib import admin

from .models import ChatMessage, ChatSession

# Register your models here.

admin.site.register(ChatSession)
admin.site.register(ChatMessage)
