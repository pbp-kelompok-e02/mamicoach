from __future__ import annotations

from datetime import timedelta
from typing import Iterable, List, Optional

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from booking.models import Booking
from chat.models import ChatAttachment, ChatMessage, ChatSession
from courses_and_coach.models import Category, Course
from reviews.models import Review
from user_profile.models import CoachProfile


DEFAULT_USER_PREFIX = "testuser"
DEFAULT_COACH_PREFIX = "testcoach"


def _ensure_categories() -> List[Category]:
    categories = list(Category.objects.all()[:3])
    if categories:
        return categories

    return [
        Category.objects.create(name="Fitness", description="Fitness training"),
        Category.objects.create(name="Yoga", description="Yoga classes"),
        Category.objects.create(name="Basketball", description="Basketball coaching"),
    ]


def _get_or_create_user(username: str, password: str, *, email: str = "") -> User:
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email or f"{username}@example.com",
            "first_name": username[:30],
            "last_name": "",
        },
    )
    if created:
        user.set_password(password)
        user.save(update_fields=["password"])
    return user


def _create_test_users(*, user_count: int, coach_count: int, password: str) -> tuple[List[User], List[User]]:
    regular_users: List[User] = []
    coach_users: List[User] = []

    for i in range(1, user_count + 1):
        u = _get_or_create_user(
            f"{DEFAULT_USER_PREFIX}{i}",
            password,
            email=f"{DEFAULT_USER_PREFIX}{i}@test.com",
        )
        # keep names stable
        if u.first_name.startswith(DEFAULT_USER_PREFIX):
            u.first_name = f"Test{i}"
            u.last_name = "User"
            u.save(update_fields=["first_name", "last_name"])
        regular_users.append(u)

    for i in range(1, coach_count + 1):
        coach_user = _get_or_create_user(
            f"{DEFAULT_COACH_PREFIX}{i}",
            password,
            email=f"{DEFAULT_COACH_PREFIX}{i}@test.com",
        )
        if coach_user.first_name.startswith(DEFAULT_COACH_PREFIX):
            coach_user.first_name = f"Coach{i}"
            coach_user.last_name = "Test"
            coach_user.save(update_fields=["first_name", "last_name"])

        CoachProfile.objects.get_or_create(
            user=coach_user,
            defaults={
                "bio": "Experienced coach specializing in various sports.",
                "expertise": ["Fitness", "Yoga", "Basketball"],
                "rating": 4.5 + (i * 0.1),
                "rating_count": 10 + (i * 5),
                "total_minutes_coached": 1200 + (i * 300),
                "verified": True,
            },
        )

        coach_users.append(coach_user)

    return regular_users, coach_users


def _create_courses(*, coach_users: List[User], course_count: int) -> List[Course]:
    categories = _ensure_categories()

    base_courses = [
        {
            "title": "Beginner Fitness Training",
            "description": "Perfect for those starting their fitness journey",
            "location": "Jakarta Sports Center",
            "price": 150000,
            "duration": 60,
        },
        {
            "title": "Yoga for Flexibility",
            "description": "Improve your flexibility and balance",
            "location": "Serenity Yoga Studio",
            "price": 120000,
            "duration": 90,
        },
        {
            "title": "Basketball Skills Training",
            "description": "Learn shooting and dribbling techniques",
            "location": "Community Basketball Court",
            "price": 180000,
            "duration": 120,
        },
    ]

    courses: List[Course] = []
    for i in range(course_count):
        spec = base_courses[i % len(base_courses)]
        coach_user = coach_users[i % len(coach_users)]
        coach_profile = coach_user.coachprofile
        category = categories[i % len(categories)]

        course, _ = Course.objects.get_or_create(
            title=spec["title"],
            coach=coach_profile,
            defaults={
                "description": spec["description"],
                "category": category,
                "location": spec["location"],
                "price": spec["price"],
                "duration": spec["duration"],
                "thumbnail_url": category.thumbnail_url,
            },
        )
        courses.append(course)

    return courses


def _create_bookings(*, users: List[User], courses: List[Course], per_user: int) -> List[Booking]:
    if not users or not courses:
        return []

    bookings: List[Booking] = []
    now = timezone.now()

    # Create a few done bookings per user so reviews can exist
    idx = 0
    for user in users:
        for _ in range(per_user):
            course = courses[idx % len(courses)]
            coach_profile = course.coach

            start = now - timedelta(days=10 + idx)
            end = start + timedelta(minutes=course.duration)

            booking, _ = Booking.objects.get_or_create(
                user=user,
                course=course,
                coach=coach_profile,
                defaults={
                    "start_datetime": start,
                    "end_datetime": end,
                    "status": "done",
                },
            )
            # make sure it is "done" for review eligibility
            if booking.status != "done":
                booking.status = "done"
                booking.start_datetime = booking.start_datetime or start
                booking.end_datetime = booking.end_datetime or end
                booking.save(update_fields=["status", "start_datetime", "end_datetime"])

            bookings.append(booking)
            idx += 1

    return bookings


def _seed_reviews(bookings: Iterable[Booking]) -> int:
    contents = [
        "Great coaching session! Very patient and knowledgeable.",
        "Excellent experience. Learned a lot in just one session.",
        "Good coach but could improve on time management.",
        "Amazing! The techniques really helped improve my game.",
        "Very professional and friendly. Highly recommend!",
    ]

    created = 0
    for i, booking in enumerate(bookings):
        rating = 4 if i % 4 == 2 else 5
        is_anonymous = i % 3 == 0

        _, was_created = Review.objects.get_or_create(
            booking=booking,
            defaults={
                "user": booking.user,
                "course": booking.course,
                "coach": booking.coach,
                "rating": rating,
                "content": contents[i % len(contents)],
                "is_anonymous": is_anonymous,
            },
        )
        if was_created:
            created += 1

    return created


def _seed_chat(*, users: List[User], coaches: List[User], messages_per_session: int) -> tuple[int, int]:
    if not users or not coaches:
        return 0, 0

    sessions_created = 0
    messages_created = 0

    now = timezone.now()

    for i, user in enumerate(users):
        coach = coaches[i % len(coaches)]
        session, session_created = ChatSession.objects.get_or_create(
            user=user,
            coach=coach,
            defaults={"started_at": now - timedelta(days=5 + i)},
        )
        if session_created:
            sessions_created += 1

        # Only seed messages if none exist to keep reruns idempotent
        if session.messages.exists():
            continue

        conversation = [
            (user, "Hi! I'm interested in booking a session."),
            (coach, "Hello! I'd be happy to help. What are you looking to improve?"),
            (user, "I want to work on my technique and endurance."),
            (coach, "Great! I have availability this week. Would Thursday work for you?"),
            (user, "Thursday sounds perfect! What time?"),
        ]

        # Trim/extend to requested length
        if messages_per_session <= len(conversation):
            conversation = conversation[:messages_per_session]
        else:
            extra_needed = messages_per_session - len(conversation)
            for n in range(extra_needed):
                conversation.append((coach if n % 2 == 0 else user, f"Follow up message {n+1}"))

        for offset, (sender, content) in enumerate(conversation):
            ChatMessage.objects.create(
                session=session,
                sender=sender,
                content=content,
                timestamp=now - timedelta(days=5 + i, minutes=(len(conversation) - offset)),
                read=(offset < (len(conversation) - 1)),
            )
            messages_created += 1

        session.last_message_at = now
        session.save(update_fields=["last_message_at"])

    return sessions_created, messages_created


def _seed_chat_attachments() -> int:
    courses = list(Course.objects.all()[:2])
    bookings = list(Booking.objects.all()[:2])
    messages = list(ChatMessage.objects.all()[:4])

    if not messages:
        return 0

    created = 0

    if courses:
        course = courses[0]
        message = messages[0]
        _, was_created = ChatAttachment.objects.get_or_create(
            message=message,
            attachment_type="course",
            defaults={
                "course_id": course.id,
                "course_name": course.title,
            },
        )
        if was_created:
            created += 1

    if bookings and len(messages) > 2:
        booking = bookings[0]
        message = messages[2]
        _, was_created = ChatAttachment.objects.get_or_create(
            message=message,
            attachment_type="booking",
            defaults={
                "booking_id": booking.id,
            },
        )
        if was_created:
            created += 1

    return created


@transaction.atomic
def _reset_seeded_data(stdout) -> None:
    # Delete in dependency order. Keep courses/categories by default (they may be real data).
    seeded_user_q = User.objects.filter(username__startswith=DEFAULT_USER_PREFIX)
    seeded_coach_q = User.objects.filter(username__startswith=DEFAULT_COACH_PREFIX)

    ChatSession.objects.filter(user__in=seeded_user_q).delete()
    ChatSession.objects.filter(coach__in=seeded_coach_q).delete()

    Review.objects.filter(user__in=seeded_user_q).delete()
    Booking.objects.filter(user__in=seeded_user_q).delete()

    CoachProfile.objects.filter(user__in=seeded_coach_q).delete()

    seeded_user_q.delete()
    seeded_coach_q.delete()

    stdout.write("✓ Reset complete (seeded users/coaches/bookings/reviews/chats removed).")


class Command(BaseCommand):
    help = "Seed demo data for reviews + chat (users, coaches, courses, bookings, reviews, chat sessions/messages)."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=3, help="Number of test users to create")
        parser.add_argument("--coaches", type=int, default=2, help="Number of test coaches to create")
        parser.add_argument("--courses", type=int, default=3, help="Number of courses to ensure")
        parser.add_argument(
            "--bookings-per-user",
            type=int,
            default=1,
            help="Number of completed bookings to create per test user",
        )
        parser.add_argument(
            "--messages-per-session",
            type=int,
            default=5,
            help="Messages to seed per chat session (only when the session has no messages)",
        )
        parser.add_argument(
            "--password",
            type=str,
            default="password123",
            help="Password for all created accounts",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previously seeded demo users/coaches and related data before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            _reset_seeded_data(self.stdout)

        user_count = max(0, int(options["users"]))
        coach_count = max(1, int(options["coaches"]))
        course_count = max(1, int(options["courses"]))
        bookings_per_user = max(0, int(options["bookings_per_user"]))
        messages_per_session = max(1, int(options["messages_per_session"]))
        password = str(options["password"]) or "password123"

        self.stdout.write("=" * 60)
        self.stdout.write("SEEDING DEMO DATA (REVIEWS + CHAT)")
        self.stdout.write("=" * 60)

        users, coaches = _create_test_users(
            user_count=user_count,
            coach_count=coach_count,
            password=password,
        )
        self.stdout.write(f"✓ Users ensured: {len(users)} | Coaches ensured: {len(coaches)}")

        courses = _create_courses(coach_users=coaches, course_count=course_count)
        self.stdout.write(f"✓ Courses ensured: {len(courses)}")

        bookings = _create_bookings(users=users, courses=courses, per_user=bookings_per_user)
        self.stdout.write(f"✓ Bookings ensured: {len(bookings)}")

        reviews_created = _seed_reviews(bookings)
        self.stdout.write(f"✓ Reviews seeded: {reviews_created} created")

        sessions_created, messages_created = _seed_chat(
            users=users,
            coaches=coaches,
            messages_per_session=messages_per_session,
        )
        self.stdout.write(f"✓ Chat seeded: {sessions_created} sessions created, {messages_created} messages created")

        attachments_created = _seed_chat_attachments()
        self.stdout.write(f"✓ Chat attachments seeded: {attachments_created} created")

        self.stdout.write("\nTest accounts:")
        self.stdout.write(f"  Users: {DEFAULT_USER_PREFIX}1..{DEFAULT_USER_PREFIX}{user_count}")
        self.stdout.write(f"  Coaches: {DEFAULT_COACH_PREFIX}1..{DEFAULT_COACH_PREFIX}{coach_count}")
        self.stdout.write(f"  Password: {password}")
