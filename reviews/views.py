from django.shortcuts import render
from datetime import datetime

# Create your views here.

def show_sample_review(request):
    # Sample hardcoded reviews data
    sample_reviews = [
        {
            'reviewer_name': 'Jenny Wilson',
            'reviewer_role': 'Ibu Rumah Tangga',
            'reviewer_avatar': 'https://i.pravatar.cc/100?img=1',
            'rating': 4,
            'comment': 'Ut pharetra ipsum nec leo blandit, sit amet tincidunt eros pharetra. Nam sed imperdiet turpis. In hac habitasse platea dictumst. Praesent nulla massa, hendrerit vestibulum gravida in, feugiat auctor felis.\n\nUt pharetra ipsum nec leo blandit, sit amet tincidunt eros pharetra. Nam sed imperdiet turpis. In hac habitasse platea dictumst.',
            'created_at': datetime(2024, 10, 15),
            'is_anonymous': False,
            'course_name': 'Kelas Yoga Chi Space Studio',
            'show_course_info': True,
        },
        {
            'reviewer_name': 'Sarah Johnson',
            'reviewer_role': 'Working Professional',
            'reviewer_avatar': 'https://i.pravatar.cc/100?img=2',
            'rating': 5,
            'comment': 'Amazing experience! The coach was very professional and patient. I learned so much in just one session. The techniques were easy to follow and I can already see improvements in my flexibility.',
            'created_at': datetime(2024, 10, 12),
            'is_anonymous': False,
            'course_name': 'Advanced Pilates Studio',
            'show_course_info': True,
        },
        {
            'reviewer_name': 'Anonymous',
            'reviewer_role': 'Student',
            'reviewer_avatar': 'https://i.pravatar.cc/100?img=3',
            'rating': 3,
            'comment': 'Good class overall, but I think the pace could be a bit slower for beginners. The coach knows what they are doing but sometimes goes too fast.',
            'created_at': datetime(2024, 10, 10),
            'is_anonymous': True,
            'course_name': 'Cardio Fitness Pro',
            'show_course_info': True,
        },
        {
            'reviewer_name': 'Michael Chen',
            'reviewer_role': 'Fitness Enthusiast',
            'reviewer_avatar': 'https://i.pravatar.cc/100?img=4',
            'rating': 5,
            'comment': 'Excellent coaching! Very detailed explanations and personalized feedback. The coach really cares about proper form and safety. Highly recommend this class to anyone looking to improve their fitness.',
            'created_at': datetime(2024, 10, 8),
            'is_anonymous': False,
            'course_name': 'Strength Training',
            'show_course_info': True,
        },
        {
            'reviewer_name': 'Lisa Rodriguez',
            'reviewer_role': 'Yoga Instructor',
            'reviewer_avatar': 'https://i.pravatar.cc/100?img=5',
            'rating': 4,
            'comment': 'Great class with good energy. The coach has a nice teaching style and creates a welcoming environment. Would definitely come back for more sessions.',
            'created_at': datetime(2024, 10, 5),
            'is_anonymous': False,
            'course_name': 'Meditation & Mindfulness',
            'show_course_info': True,
        },
    ]
    
    ctx = {
        'reviews': sample_reviews
    }
    return render(request, "pages/sample_review.html", context=ctx)


def create_review(request):
    ctx = {
        'bookingId': "123",
        'courseName': "Class A",
        'courseImageUrl': "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQcTY50AnR35-aKaONIPoeLNh_KrvAq9bwD7A&s",
        'coachName': "Coach B",
        'bookedDate': "17:39 at 20 May 2024",
        'duration': "60 minutes",
    }
    return render(request, "pages/create_review.html", context=ctx)


def edit_review(request):
    ctx = {
        'bookingId': "123",
        'courseName': "Class A",
        'courseImageUrl': "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQcTY50AnR35-aKaONIPoeLNh_KrvAq9bwD7A&s",
        'coachName': "Coach B",
        'bookedDate': "17:39 at 20 May 2024",
        'duration': "60 minutes",
    }
    return render(request, "pages/edit_review.html", context=ctx)
