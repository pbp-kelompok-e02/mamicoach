from django.db import models
from django.contrib.auth.models import User
import uuid


# Create your models here.
class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    coach = models.ForeignKey(User, related_name='coach_sessions', on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ChatSession between {self.user.username} and {self.coach.username} started at {self.started_at}"
    
    def get_other_user(self, current_user):
        """Get the other participant in the chat session"""
        return self.coach if current_user == self.user else self.user
    
    def get_last_message(self):
        """Get the last message in this chat session"""
        return self.messages.order_by('-timestamp').first()


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    reply_to = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='replies'
    )

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"
    
    def is_sent_by(self, user):
        """Check if the message was sent by the given user"""
        return self.sender == user


class ChatAttachment(models.Model):
    """Model for storing chat message attachments"""
    ATTACHMENT_TYPE_CHOICES = [
        ('image', 'Image'),
        ('file', 'File'),
        ('course', 'Course'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(ChatMessage, related_name='attachments', on_delete=models.CASCADE)
    attachment_type = models.CharField(max_length=20, choices=ATTACHMENT_TYPE_CHOICES, default='file')
    file = models.FileField(upload_to='chat_attachments/%Y/%m/%d/')
    thumbnail = models.ImageField(upload_to='chat_attachments/thumbnails/%Y/%m/%d/', null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Metadata for different attachment types
    course_id = models.IntegerField(null=True, blank=True)  # For course attachments
    course_name = models.CharField(max_length=255, null=True, blank=True)  # For course attachments
    file_name = models.CharField(max_length=255, null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)  # Size in bytes

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f"{self.get_attachment_type_display()} from {self.message.sender.username}"
