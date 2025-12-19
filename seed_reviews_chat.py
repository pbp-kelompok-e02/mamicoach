"""
Seed script for populating reviews and chat data for testing.
Run: python manage.py shell < seed_reviews_chat.py
Or: python seed_reviews_chat.py
"""

import os
import django
import sys
from datetime import timedelta
from django.utils import timezone

# Setup Django
if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mami_coach.settings')
    django.setup()

from django.contrib.auth.models import User
from booking.models import Booking
from courses_and_coach.models import Course, CoachProfile
from reviews.models import Review
from chat.models import ChatSession, ChatMessage, ChatAttachment

def create_test_users():
    """Create test users: 2 coaches, 3 regular users"""
    users = []
    
    # Regular users
    for i in range(1, 4):
        user, created = User.objects.get_or_create(
            username=f'testuser{i}',
            defaults={
                'email': f'testuser{i}@test.com',
                'first_name': f'Test{i}',
                'last_name': 'User',
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            print(f"✓ Created user: {user.username}")
        users.append(user)
    
    # Coach users
    for i in range(1, 3):
        coach_user, created = User.objects.get_or_create(
            username=f'testcoach{i}',
            defaults={
                'email': f'testcoach{i}@test.com',
                'first_name': f'Coach{i}',
                'last_name': 'Test',
            }
        )
        if created:
            coach_user.set_password('password123')
            coach_user.save()
            print(f"✓ Created coach user: {coach_user.username}")
        
        # Create coach profile
        coach_profile, created = CoachProfile.objects.get_or_create(
            user=coach_user,
            defaults={
                'bio': f'Experienced coach specializing in various sports.',
                'expertise': ['Fitness', 'Yoga', 'Basketball'],
                'rating': 4.5 + (i * 0.2),
                'rating_count': 10 + (i * 5),
                'total_minutes_coached': 1200 + (i * 300),
                'verified': True,
            }
        )
        if created:
            print(f"✓ Created coach profile for: {coach_user.username}")
        users.append(coach_user)
    
    return users

def create_test_courses(coach_users):
    """Create test courses if none exist"""
    from courses_and_coach.models import Category
    
    courses = []
    categories = Category.objects.all()[:3]
    
    if not categories:
        print("⚠ No categories found. Creating default categories...")
        categories = [
            Category.objects.create(name="Fitness", description="Fitness training"),
            Category.objects.create(name="Yoga", description="Yoga classes"),
            Category.objects.create(name="Basketball", description="Basketball coaching"),
        ]
    
    course_data = [
        {
            'title': 'Beginner Fitness Training',
            'description': 'Perfect for those starting their fitness journey',
            'location': 'Jakarta Sports Center',
            'price': 150000,
            'duration': 60,
        },
        {
            'title': 'Yoga for Flexibility',
            'description': 'Improve your flexibility and balance',
            'location': 'Serenity Yoga Studio',
            'price': 120000,
            'duration': 90,
        },
        {
            'title': 'Basketball Skills Training',
            'description': 'Learn shooting and dribbling techniques',
            'location': 'Community Basketball Court',
            'price': 180000,
            'duration': 120,
        },
    ]
    
    for i, data in enumerate(course_data):
        coach_profile = coach_users[i % len(coach_users)].coachprofile
        category = categories[i % len(categories)]
        
        course, created = Course.objects.get_or_create(
            title=data['title'],
            coach=coach_profile,
            defaults={
                'description': data['description'],
                'category': category,
                'location': data['location'],
                'price': data['price'],
                'duration': data['duration'],
                'thumbnail_url': category.thumbnail_url if hasattr(category, 'thumbnail_url') else None,
            }
        )
        if created:
            print(f"✓ Created course: {course.title}")
        courses.append(course)
    
    return courses

def create_test_bookings(users):
    """Create bookings for testing reviews"""
    bookings = []
    
    # Get coach users
    coach_users = [u for u in users if hasattr(u, 'coachprofile')]
    
    # Get or create courses
    courses = Course.objects.all()[:3]
    if not courses:
        print("  Creating test courses...")
        courses = create_test_courses(coach_users)
    
    if not courses:
        print("⚠ Failed to create courses")
        return bookings
    
    # Create bookings
    regular_users = [u for u in users if not hasattr(u, 'coachprofile')]
    for i, course in enumerate(courses):
        user = regular_users[i % len(regular_users)]
        
        booking, created = Booking.objects.get_or_create(
            user=user,
            course=course,
            defaults={
                'coach': course.coach,
                'start_datetime': timezone.now() - timedelta(days=10 + i),
                'end_datetime': timezone.now() - timedelta(days=10 + i, hours=-2),
                'status': 'done',
            }
        )
        if created:
            print(f"✓ Created booking: {user.username} -> {course.title}")
        bookings.append(booking)
    
    return bookings

def seed_reviews(bookings):
    """Create reviews for completed bookings"""
    if not bookings:
        print("⚠ No bookings available for reviews")
        return
    
    review_contents = [
        "Great coaching session! Very patient and knowledgeable.",
        "Excellent experience. Learned a lot in just one session.",
        "Good coach but could improve on time management.",
        "Amazing! The techniques really helped improve my game.",
        "Very professional and friendly. Highly recommend!",
    ]
    
    created = 0
    for i, booking in enumerate(bookings):
        rating = 4 if i % 4 == 2 else 5  # Mix of 4 and 5 stars
        is_anonymous = i % 3 == 0  # Some anonymous reviews
        
        review, created_flag = Review.objects.get_or_create(
            booking=booking,
            defaults={
                'user': booking.user,
                'course': booking.course,
                'coach': booking.coach,
                'rating': rating,
                'content': review_contents[i % len(review_contents)],
                'is_anonymous': is_anonymous,
            }
        )
        if created_flag:
            created += 1
            anon_text = " (anonymous)" if is_anonymous else ""
            print(f"✓ Created review: {rating}★ for {booking.course.title}{anon_text}")
    
    print(f"\n✓ Reviews seeded: {created} created")

def seed_chat_sessions_and_messages(users):
    """Create chat sessions and messages"""
    coaches = User.objects.filter(coachprofile__isnull=False)[:2]
    regular_users = User.objects.exclude(coachprofile__isnull=False)[:3]
    
    if not coaches or not regular_users:
        print("⚠ Need coaches and users for chat")
        return
    
    sessions_created = 0
    messages_created = 0
    
    # Create sessions between users and coaches
    for i, user in enumerate(regular_users):
        coach = coaches[i % len(coaches)]
        
        session, created = ChatSession.objects.get_or_create(
            user=user,
            coach=coach,
            defaults={
                'started_at': timezone.now() - timedelta(days=5 + i),
            }
        )
        
        if created:
            sessions_created += 1
            print(f"✓ Created chat session: {user.username} <-> {coach.username}")
            
            # Create messages in this session
            messages_data = [
                (user, "Hi! I'm interested in booking a session.", 0),
                (coach, "Hello! I'd be happy to help. What are you looking to improve?", 1),
                (user, "I want to work on my technique and endurance.", 2),
                (coach, "Great! I have availability this week. Would Thursday work for you?", 3),
                (user, "Thursday sounds perfect! What time?", 4),
            ]
            
            for sender, content, offset in messages_data:
                message = ChatMessage.objects.create(
                    session=session,
                    sender=sender,
                    content=content,
                    timestamp=timezone.now() - timedelta(days=5 + i, hours=offset),
                    read=(offset < 4),  # Last message unread
                )
                messages_created += 1
            
            session.last_message_at = timezone.now() - timedelta(days=5 + i, hours=4)
            session.save()
    
    print(f"\n✓ Chat seeded: {sessions_created} sessions, {messages_created} messages")

def seed_chat_attachments():
    """Create some test attachments for chat messages"""
    courses = Course.objects.all()[:2]
    bookings = Booking.objects.all()[:2]
    messages = ChatMessage.objects.all()[:4]
    
    if not messages:
        print("⚠ No messages available for attachments")
        return
    
    attachments_created = 0
    
    # Attach course to first message
    if courses and messages:
        course = courses[0]
        message = messages[0]
        attachment, created = ChatAttachment.objects.get_or_create(
            message=message,
            attachment_type='course',
            defaults={
                'course_id': course.id,
                'course_name': course.title,
            }
        )
        if created:
            attachments_created += 1
            print(f"✓ Attached course: {course.title}")
    
    # Attach booking to third message
    if bookings and len(messages) > 2:
        booking = bookings[0]
        message = messages[2]
        attachment, created = ChatAttachment.objects.get_or_create(
            message=message,
            attachment_type='booking',
            defaults={
                'booking_id': booking.id,
            }
        )
        if created:
            attachments_created += 1
            print(f"✓ Attached booking: {booking.id}")
    
    print(f"\n✓ Attachments seeded: {attachments_created} created")

def main():
    print("\n" + "="*60)
    print("SEEDING REVIEWS AND CHAT DATA")
    print("="*60 + "\n")
    
    print("Step 1: Creating test users...")
    users = create_test_users()
    
    print("\nStep 2: Creating test bookings...")
    bookings = create_test_bookings(users)
    
    print("\nStep 3: Seeding reviews...")
    seed_reviews(bookings)
    
    print("\nStep 4: Seeding chat sessions and messages...")
    seed_chat_sessions_and_messages(users)
    
    print("\nStep 5: Adding chat attachments...")
    seed_chat_attachments()
    
    print("\n" + "="*60)
    print("SEEDING COMPLETE!")
    print("="*60)
    print("\nTest accounts created:")
    print("  Users: testuser1, testuser2, testuser3")
    print("  Coaches: testcoach1, testcoach2")
    print("  Password for all: password123")
    print("\n")

if __name__ == '__main__':
    main()
