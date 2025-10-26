from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
import json
import uuid

from .models import ChatSession, ChatMessage, ChatAttachment
from user_profile.models import CoachProfile, UserProfile
from courses_and_coach.models import Course
from booking.models import Booking


class ChatTestSetUp(TestCase):
    """Base test class with common setup for chat tests"""
    
    def setUp(self):
        """Set up test users, profiles, and initial data"""
        self.client = Client()
        
        # Create regular user
        self.user = User.objects.create_user(
            username='testuser',
            email='testuser@example.com',
            password='testpass123'
        )
        
        # Create coach user
        self.coach = User.objects.create_user(
            username='testcoach',
            email='testcoach@example.com',
            password='testpass123'
        )
        
        # Create coach profile
        self.coach_profile = CoachProfile.objects.create(
            user=self.coach,
            bio='Test coach bio'
        )
        
        # Create user profile
        self.user_profile = UserProfile.objects.create(
            user=self.user
        )
        
        # Create another user for multi-user tests
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='otheruser@example.com',
            password='testpass123'
        )
        
        # Create another coach for tests
        self.other_coach = User.objects.create_user(
            username='othercoach',
            email='othercoach@example.com',
            password='testpass123'
        )
        CoachProfile.objects.create(
            user=self.other_coach,
            bio='Other coach bio'
        )
        
        # Create course
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            coach=self.coach_profile,
            location='Online',
            price=100000,
            duration=60
        )
        
        # Create booking
        self.booking = Booking.objects.create(
            user=self.user,
            course=self.course,
            coach=self.coach_profile,
            start_datetime=timezone.now(),
            end_datetime=timezone.now() + timezone.timedelta(hours=1),
            status='confirmed'
        )
        
        # Create chat session
        self.chat_session = ChatSession.objects.create(
            user=self.user,
            coach=self.coach
        )


class ChatIndexViewTest(ChatTestSetUp):
    """Test chat_index view"""
    
    def test_chat_index_requires_login(self):
        """Test that chat index requires authentication"""
        response = self.client.get(reverse('chat:chat_index'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_chat_index_logged_in(self):
        """Test that chat index loads for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('chat:chat_index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/chat_interface.html')


class ChatDetailViewTest(ChatTestSetUp):
    """Test chat_detail view"""
    
    def test_chat_detail_requires_login(self):
        """Test that chat detail requires authentication"""
        response = self.client.get(
            reverse('chat:chat_detail', kwargs={'session_id': self.chat_session.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_chat_detail_user_authorized(self):
        """Test that user can access their own chat session"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('chat:chat_detail', kwargs={'session_id': self.chat_session.id})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_chat_detail_coach_authorized(self):
        """Test that coach can access their own chat session"""
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.get(
            reverse('chat:chat_detail', kwargs={'session_id': self.chat_session.id})
        )
        self.assertEqual(response.status_code, 200)
    
    def test_chat_detail_unauthorized_user(self):
        """Test that unauthorized user cannot access chat session"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(
            reverse('chat:chat_detail', kwargs={'session_id': self.chat_session.id})
        )
        self.assertEqual(response.status_code, 403)
    
    def test_chat_detail_nonexistent_session(self):
        """Test accessing non-existent chat session"""
        self.client.login(username='testuser', password='testpass123')
        fake_id = uuid.uuid4()
        response = self.client.get(
            reverse('chat:chat_detail', kwargs={'session_id': fake_id})
        )
        self.assertEqual(response.status_code, 404)
    
    def test_chat_detail_with_pre_attachment_data(self):
        """Test chat detail with pre-attachment data in URL params"""
        self.client.login(username='testuser', password='testpass123')
        pre_data = json.dumps({'id': self.booking.id, 'type': 'booking'})
        response = self.client.get(
            reverse('chat:chat_detail', kwargs={'session_id': self.chat_session.id}),
            {'pre_attachment_type': 'booking', 'pre_attachment_data': pre_data}
        )
        self.assertEqual(response.status_code, 200)


class GetChatSessionsTest(ChatTestSetUp):
    """Test get_chat_sessions endpoint"""
    
    def test_get_sessions_requires_login(self):
        """Test that endpoint requires authentication"""
        response = self.client.get(reverse('chat:get_chat_sessions'))
        self.assertEqual(response.status_code, 302)
    
    def test_get_sessions_for_user(self):
        """Test getting chat sessions for regular user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('chat:get_chat_sessions'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('sessions', data)
    
    def test_get_sessions_for_coach(self):
        """Test getting chat sessions for coach"""
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.get(reverse('chat:get_chat_sessions'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('sessions', data)
    
    def test_get_sessions_with_messages(self):
        """Test getting sessions includes message info"""
        # Create a message
        ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test message'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('chat:get_chat_sessions'))
        data = json.loads(response.content)
        
        self.assertEqual(len(data['sessions']), 1)
        self.assertIn('last_message', data['sessions'][0])
    
    def test_get_sessions_unread_count(self):
        """Test unread message count in sessions"""
        # Create unread message from coach
        ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.coach,
            content='Unread message',
            read=False
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('chat:get_chat_sessions'))
        data = json.loads(response.content)
        
        self.assertEqual(data['sessions'][0]['unread_count'], 1)


class GetMessagesTest(ChatTestSetUp):
    """Test get_messages endpoint"""
    
    def test_get_messages_requires_login(self):
        """Test endpoint requires authentication"""
        response = self.client.get(
            reverse('chat:get_messages', kwargs={'session_id': self.chat_session.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_get_messages_authorized_user(self):
        """Test user can get messages from their session"""
        ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Hello coach'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('chat:get_messages', kwargs={'session_id': self.chat_session.id})
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['messages']), 1)
    
    def test_get_messages_unauthorized_user(self):
        """Test unauthorized user cannot get messages"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(
            reverse('chat:get_messages', kwargs={'session_id': self.chat_session.id})
        )
        self.assertEqual(response.status_code, 403)
    
    def test_get_messages_marks_as_read(self):
        """Test that messages are marked as read when retrieved"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.coach,
            content='Message to read',
            read=False
        )
        
        self.client.login(username='testuser', password='testpass123')
        self.client.get(
            reverse('chat:get_messages', kwargs={'session_id': self.chat_session.id})
        )
        
        message.refresh_from_db()
        self.assertTrue(message.read)
    
    def test_get_messages_with_reply(self):
        """Test getting messages with reply_to data"""
        original_message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.coach,
            content='Original message'
        )
        
        reply_message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Reply message',
            reply_to=original_message
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('chat:get_messages', kwargs={'session_id': self.chat_session.id})
        )
        data = json.loads(response.content)
        
        self.assertIsNotNone(data['messages'][1]['reply_to'])
        self.assertEqual(data['messages'][1]['reply_to']['content'], 'Original message')


class SendMessageTest(ChatTestSetUp):
    """Test send_message endpoint"""
    
    def test_send_message_requires_login(self):
        """Test endpoint requires authentication"""
        response = self.client.post(
            reverse('chat:send_message'),
            data=json.dumps({'session_id': str(self.chat_session.id), 'content': 'Hello'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_send_message_requires_post(self):
        """Test endpoint requires POST method"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('chat:send_message'))
        self.assertEqual(response.status_code, 405)
    
    def test_send_message_success(self):
        """Test successfully sending a message"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:send_message'),
            data=json.dumps({
                'session_id': str(self.chat_session.id),
                'content': 'Hello coach!'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['message']['content'], 'Hello coach!')
    
    def test_send_message_empty_content(self):
        """Test sending empty message fails"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:send_message'),
            data=json.dumps({
                'session_id': str(self.chat_session.id),
                'content': ''
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_send_message_no_session_id(self):
        """Test sending message without session_id fails"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:send_message'),
            data=json.dumps({'content': 'Hello'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_send_message_unauthorized_session(self):
        """Test unauthorized user cannot send message"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.post(
            reverse('chat:send_message'),
            data=json.dumps({
                'session_id': str(self.chat_session.id),
                'content': 'Unauthorized message'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
    
    def test_send_message_with_reply(self):
        """Test sending message with reply_to"""
        original_message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.coach,
            content='Original'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:send_message'),
            data=json.dumps({
                'session_id': str(self.chat_session.id),
                'content': 'Reply message',
                'reply_to_id': original_message.id
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['message']['reply_to']['id'], original_message.id)
    
    def test_send_message_sanitizes_html(self):
        """Test that HTML tags are stripped from message"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:send_message'),
            data=json.dumps({
                'session_id': str(self.chat_session.id),
                'content': '<b>Hello</b> <i>world</i>'
            }),
            content_type='application/json'
        )
        data = json.loads(response.content)
        # strip_tags removes HTML tags but keeps the text content
        self.assertEqual(data['message']['content'], 'Hello world')


class MarkMessagesReadTest(ChatTestSetUp):
    """Test mark_messages_read endpoint"""
    
    def test_mark_read_requires_login(self):
        """Test endpoint requires authentication"""
        response = self.client.post(
            reverse('chat:mark_messages_read'),
            data=json.dumps({'session_id': str(self.chat_session.id)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_mark_read_success(self):
        """Test successfully marking messages as read"""
        # Create unread messages
        ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.coach,
            content='Message 1',
            read=False
        )
        ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.coach,
            content='Message 2',
            read=False
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:mark_messages_read'),
            data=json.dumps({'session_id': str(self.chat_session.id)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['updated_count'], 2)
    
    def test_mark_read_unauthorized(self):
        """Test unauthorized user cannot mark messages as read"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.post(
            reverse('chat:mark_messages_read'),
            data=json.dumps({'session_id': str(self.chat_session.id)}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)


class CreateChatWithCoachTest(ChatTestSetUp):
    """Test create_chat_with_coach endpoint"""
    
    def test_create_chat_requires_login(self):
        """Test endpoint requires authentication"""
        response = self.client.post(
            reverse('chat:create_chat_with_coach', kwargs={'coach_id': self.coach.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_create_chat_success(self):
        """Test successfully creating new chat session"""
        # Create new coach
        new_coach = User.objects.create_user(
            username='newcoach',
            password='testpass123'
        )
        CoachProfile.objects.create(user=new_coach, bio='New coach')
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:create_chat_with_coach', kwargs={'coach_id': new_coach.id})
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('session_id', data)
    
    def test_create_chat_existing_session(self):
        """Test creating chat with existing session returns existing session"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:create_chat_with_coach', kwargs={'coach_id': self.coach.id})
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(str(data['session_id']), str(self.chat_session.id))
    
    def test_create_chat_not_a_coach(self):
        """Test creating chat with non-coach fails"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:create_chat_with_coach', kwargs={'coach_id': self.other_user.id})
        )
        self.assertEqual(response.status_code, 400)
    
    def test_create_chat_with_self(self):
        """Test user cannot create chat with themselves"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:create_chat_with_coach', kwargs={'coach_id': self.user.id})
        )
        self.assertEqual(response.status_code, 400)


class UploadAttachmentTest(ChatTestSetUp):
    """Test upload_attachment endpoint"""
    
    def test_upload_requires_login(self):
        """Test endpoint requires authentication"""
        response = self.client.post(
            reverse('chat:upload_attachment', kwargs={'session_id': self.chat_session.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_upload_requires_message_first(self):
        """Test upload requires a message to exist"""
        self.client.login(username='testuser', password='testpass123')
        file = SimpleUploadedFile('test.txt', b'file content')
        response = self.client.post(
            reverse('chat:upload_attachment', kwargs={'session_id': self.chat_session.id}),
            {'file': file, 'type': 'file', 'message_id': '999'}
        )
        self.assertEqual(response.status_code, 400)
    
    def test_upload_no_file(self):
        """Test upload without file fails"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test message'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:upload_attachment', kwargs={'session_id': self.chat_session.id}),
            {'type': 'file', 'message_id': message.id}
        )
        self.assertEqual(response.status_code, 400)
    
    def test_upload_file_success(self):
        """Test successfully uploading a file"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test message'
        )
        
        self.client.login(username='testuser', password='testpass123')
        file = SimpleUploadedFile('test.txt', b'file content')
        response = self.client.post(
            reverse('chat:upload_attachment', kwargs={'session_id': self.chat_session.id}),
            {'file': file, 'type': 'file', 'message_id': message.id}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_upload_file_too_large(self):
        """Test uploading oversized file fails"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test message'
        )
        
        # Create a file larger than 10MB
        large_content = b'x' * (11 * 1024 * 1024)
        self.client.login(username='testuser', password='testpass123')
        file = SimpleUploadedFile('large.txt', large_content)
        response = self.client.post(
            reverse('chat:upload_attachment', kwargs={'session_id': self.chat_session.id}),
            {'file': file, 'type': 'file', 'message_id': message.id}
        )
        self.assertEqual(response.status_code, 400)
    
    def test_upload_unauthorized_session(self):
        """Test unauthorized user cannot upload"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test message'
        )
        
        self.client.login(username='otheruser', password='testpass123')
        file = SimpleUploadedFile('test.txt', b'file content')
        response = self.client.post(
            reverse('chat:upload_attachment', kwargs={'session_id': self.chat_session.id}),
            {'file': file, 'type': 'file', 'message_id': message.id}
        )
        self.assertEqual(response.status_code, 403)


class CreateAttachmentTest(ChatTestSetUp):
    """Test create_attachment endpoint (for course/booking embeds)"""
    
    def test_create_attachment_requires_login(self):
        """Test endpoint requires authentication"""
        response = self.client.post(
            reverse('chat:create_attachment', kwargs={'session_id': self.chat_session.id}),
            data=json.dumps({'type': 'booking', 'booking_id': self.booking.id, 'message_id': '1'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)
    
    def test_create_booking_attachment(self):
        """Test creating booking attachment"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Check this booking'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:create_attachment', kwargs={'session_id': self.chat_session.id}),
            data=json.dumps({
                'type': 'booking',
                'booking_id': self.booking.id,
                'message_id': message.id
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_create_course_attachment(self):
        """Test creating course attachment"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Check this course'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:create_attachment', kwargs={'session_id': self.chat_session.id}),
            data=json.dumps({
                'type': 'course',
                'course_id': self.course.id,
                'message_id': message.id
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_create_attachment_invalid_type(self):
        """Test invalid attachment type fails"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test'
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(
            reverse('chat:create_attachment', kwargs={'session_id': self.chat_session.id}),
            data=json.dumps({
                'type': 'invalid_type',
                'message_id': message.id
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class PresendBookingTest(ChatTestSetUp):
    """Test presend_booking endpoint"""
    
    def test_presend_booking_requires_login(self):
        """Test endpoint requires authentication"""
        response = self.client.get(
            reverse('chat:presend_booking', kwargs={'booking_id': self.booking.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_presend_booking_user_authorized(self):
        """Test user can presend booking"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('chat:presend_booking', kwargs={'booking_id': self.booking.id})
        )
        self.assertEqual(response.status_code, 302)
        # Check redirect URL contains session_id
        self.assertIn('/chat/', response.url)
    
    def test_presend_booking_coach_authorized(self):
        """Test coach can presend booking"""
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.get(
            reverse('chat:presend_booking', kwargs={'booking_id': self.booking.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_presend_booking_unauthorized(self):
        """Test unauthorized user cannot presend booking"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(
            reverse('chat:presend_booking', kwargs={'booking_id': self.booking.id})
        )
        self.assertEqual(response.status_code, 403)
    
    def test_presend_booking_creates_session(self):
        """Test presending booking creates chat session if needed"""
        # Delete existing session
        self.chat_session.delete()
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('chat:presend_booking', kwargs={'booking_id': self.booking.id})
        )
        
        # Verify session was created
        self.assertTrue(
            ChatSession.objects.filter(user=self.user, coach=self.coach).exists()
        )


class PresendCourseTest(ChatTestSetUp):
    """Test presend_course endpoint"""
    
    def test_presend_course_requires_login(self):
        """Test endpoint requires authentication"""
        response = self.client.get(
            reverse('chat:presend_course', kwargs={'course_id': self.course.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_presend_course_user_authorized(self):
        """Test user can presend course"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('chat:presend_course', kwargs={'course_id': self.course.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_presend_course_coach_cannot_self(self):
        """Test coach cannot presend their own course"""
        self.client.login(username='testcoach', password='testpass123')
        response = self.client.get(
            reverse('chat:presend_course', kwargs={'course_id': self.course.id})
        )
        self.assertEqual(response.status_code, 302)
    
    def test_presend_course_creates_session(self):
        """Test presending course creates chat session if needed"""
        # Create a new chat session to verify it creates one
        ChatSession.objects.filter(user=self.user, coach=self.coach).delete()
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(
            reverse('chat:presend_course', kwargs={'course_id': self.course.id})
        )
        
        # Verify session was created
        self.assertTrue(
            ChatSession.objects.filter(user=self.user, coach=self.coach).exists()
        )


class ChatModelTests(ChatTestSetUp):
    """Test ChatSession and ChatMessage model methods"""
    
    def test_chat_session_get_other_user(self):
        """Test get_other_user method"""
        other = self.chat_session.get_other_user(self.user)
        self.assertEqual(other, self.coach)
        
        other = self.chat_session.get_other_user(self.coach)
        self.assertEqual(other, self.user)
    
    def test_chat_session_get_last_message(self):
        """Test get_last_message method"""
        import time
        message1 = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='First'
        )
        time.sleep(0.01)  # Small delay to ensure different timestamps
        message2 = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.coach,
            content='Second'
        )
        
        last = self.chat_session.get_last_message()
        self.assertEqual(last.pk, message2.pk)
    
    def test_chat_message_is_sent_by(self):
        """Test is_sent_by method"""
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test'
        )
        
        self.assertTrue(message.is_sent_by(self.user))
        self.assertFalse(message.is_sent_by(self.coach))
    
    def test_chat_attachment_creation(self):
        """Test ChatAttachment creation"""
        from chat.models import ChatAttachment
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test attachment'
        )
        
        attachment = ChatAttachment.objects.create(
            message=message,
            attachment_type='file',
            file_name='test.pdf',
            file_size=1024
        )
        self.assertEqual(attachment.attachment_type, 'file')
        self.assertEqual(attachment.file_name, 'test.pdf')
    
    def test_chat_attachment_str(self):
        """Test ChatAttachment string representation"""
        from chat.models import ChatAttachment
        message = ChatMessage.objects.create(
            session=self.chat_session,
            sender=self.user,
            content='Test'
        )
        
        attachment = ChatAttachment.objects.create(
            message=message,
            attachment_type='image',
            file_name='photo.jpg'
        )
        
        str_repr = str(attachment)
        self.assertIn('Image', str_repr)
        self.assertIn(self.user.username, str_repr)

