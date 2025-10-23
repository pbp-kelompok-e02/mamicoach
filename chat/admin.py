from django.contrib import admin

from .models import ChatMessage, ChatSession, ChatAttachment

# Register your models here.

class ChatAttachmentInline(admin.TabularInline):
    model = ChatAttachment
    extra = 0
    readonly_fields = ('id', 'uploaded_at')
    fields = ('attachment_type', 'file', 'file_name', 'file_size', 'uploaded_at')


class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'session', 'timestamp', 'read')
    list_filter = ('read', 'timestamp', 'session')
    search_fields = ('content', 'sender__username')
    readonly_fields = ('id', 'timestamp')
    inlines = [ChatAttachmentInline]


class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'coach', 'started_at', 'last_message_at')
    list_filter = ('started_at', 'last_message_at')
    search_fields = ('user__username', 'coach__username')
    readonly_fields = ('id', 'started_at', 'last_message_at')


class ChatAttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'attachment_type', 'file_name', 'file_size', 'uploaded_at')
    list_filter = ('attachment_type', 'uploaded_at')
    search_fields = ('file_name', 'message__sender__username')
    readonly_fields = ('id', 'uploaded_at')


admin.site.register(ChatSession, ChatSessionAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(ChatAttachment, ChatAttachmentAdmin)

