from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from courses_and_coach.models import Category, Course
from user_profile.models import CoachProfile
import random


# !! THIS FILE IS ONLY FOR DEV PURPOSES
class Command(BaseCommand):
    help = "Create sample data including categories, coaches, and courses"

    def handle(self, *args, **options):
        self.create_categories()
        self.create_coaches()
        self.create_courses()
        self.create_bookings()
        self.create_reviews()

        self.stdout.write(self.style.SUCCESS("Successfully populated all sample data!"))
    def create_reviews(self):
        """Create sample reviews based on some bookings"""
        from reviews.models import Review
        from booking.models import Booking
        from django.utils import timezone
        import random

        # Get all bookings
        bookings = list(Booking.objects.all())
        if not bookings:
            self.stdout.write(self.style.WARNING("No bookings found to seed reviews."))
            return

        # Select 8 random bookings to review
        num_reviews = min(8, len(bookings))
        sampled_bookings = random.sample(bookings, num_reviews)

        review_contents = [
            "Pelatihnya ramah dan profesional! Saya belajar banyak.",
            "Kelasnya seru dan bermanfaat, recommended banget.",
            "Materi yang diajarkan sangat jelas dan mudah diikuti.",
            "Sangat membantu untuk pemula seperti saya.",
            "Tempatnya nyaman dan pelatihnya berpengalaman.",
            "Saya suka metode pengajarannya, tidak membosankan.",
            "Kelasnya intens tapi hasilnya terasa!",
            "Akan ikut lagi di kelas berikutnya!",
        ]

        for i, booking in enumerate(sampled_bookings):
            # Avoid duplicate reviews for same user/course
            if Review.objects.filter(user=booking.user, course=booking.course).exists():
                continue
            content = review_contents[i % len(review_contents)]
            rating = random.randint(4, 5)
            is_anonymous = random.choice([True, False])
            review = Review.objects.create(
                user=booking.user,
                course=booking.course,
                coach=booking.coach,
                booking=booking,
                content=content,
                rating=rating,
                is_anonymous=is_anonymous,
                created_at=timezone.now(),
            )
            self.stdout.write(self.style.SUCCESS(f"✓ Created review for {booking.user.username} - {booking.course.title} (Rating: {rating})"))
    def create_bookings(self):
        """Create sample bookings"""
        from booking.models import Booking
        from django.utils import timezone
        # Get all users except coaches
        coach_usernames = [
            "sarah_yoga", "mike_fitness", "diana_pilates", "alex_zumba", "lisa_swim"
        ]
        users = User.objects.exclude(username__in=coach_usernames)
        # If no non-coach users, create some
        if users.count() == 0:
            for i in range(1, 6):
                user, created = User.objects.get_or_create(
                    username=f"user{i}",
                    defaults={
                        "first_name": f"User{i}",
                        "last_name": "Test",
                        "email": f"user{i}@mamicoach.com",
                    },
                )
                if created:
                    user.set_password("password123")
                    user.save()
            users = User.objects.exclude(username__in=coach_usernames)

        courses = Course.objects.all()

        # Create 20 bookings
        status_choices = [choice[0] for choice in Booking.STATUS_CHOICES]
        for i in range(20):
            user = random.choice(list(users))
            course = random.choice(list(courses))
            coach = course.coach  # Always use the course's coach
            # Generate random start and end datetime
            start_datetime = timezone.now() + timezone.timedelta(days=random.randint(1, 30), hours=random.randint(6, 18))
            duration_minutes = course.duration if hasattr(course, 'duration') and course.duration else random.choice([45, 60, 90])
            end_datetime = start_datetime + timezone.timedelta(minutes=duration_minutes)
            status = random.choice(status_choices)

            booking, created = Booking.objects.get_or_create(
                user=user,
                course=course,
                coach=coach,
                start_datetime=start_datetime,
                end_datetime=end_datetime,
                defaults={
                    "status": status,
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"Created booking (ID: {booking.pk}) for {user.username} - {course.title} ({status}) [{start_datetime} - {end_datetime}]")
                )

    def create_categories(self):
        """Create sample categories"""
        categories = [
            {
                "name": "Yoga",
                "description": "Latihan yoga untuk fleksibilitas dan ketenangan pikiran",
                "thumbnail_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "name": "Pilates",
                "description": "Latihan pilates untuk kekuatan inti dan postur tubuh",
                "thumbnail_url": "https://images.unsplash.com/photo-1518611012118-696072aa579a?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "name": "Cardio",
                "description": "Latihan kardiovaskular untuk kesehatan jantung",
                "thumbnail_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "name": "Strength Training",
                "description": "Latihan kekuatan untuk membangun massa otot",
                "thumbnail_url": "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "name": "Zumba",
                "description": "Latihan dance fitness yang menyenangkan",
                "thumbnail_url": "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "name": "Swimming",
                "description": "Latihan renang untuk seluruh tubuh",
                "thumbnail_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
        ]

        for category_data in categories:
            category, created = Category.objects.get_or_create(
                name=category_data["name"],
                defaults={
                    "description": category_data["description"],
                    "thumbnail_url": category_data["thumbnail_url"],
                },
            )
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created category: {category.name}")
                )

    def create_coaches(self):
        """Create sample coach accounts"""
        coaches_data = [
            {
                "username": "sarah_yoga",
                "first_name": "Sarah",
                "last_name": "Anderson",
                "email": "sarah.anderson@mamicoach.com",
                "bio": "Instruktur yoga bersertifikat dengan pengalaman 8 tahun. Spesialis dalam Hatha dan Vinyasa yoga untuk semua level.",
                "expertise": ["Yoga", "Meditasi", "Prenatal Yoga"],
                "rating": 4.9,
                "verified": True,
                "image_url": "https://images.unsplash.com/photo-1494790108755-2616b612b47c?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "username": "mike_fitness",
                "first_name": "Michael",
                "last_name": "Johnson",
                "email": "michael.johnson@mamicoach.com",
                "bio": "Personal trainer dengan spesialisasi strength training dan cardio. Membantu klien mencapai target fitness mereka.",
                "expertise": ["Strength Training", "Cardio", "Weight Loss"],
                "rating": 4.8,
                "verified": True,
                "image_url": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "username": "diana_pilates",
                "first_name": "Diana",
                "last_name": "Chen",
                "email": "diana.chen@mamicoach.com",
                "bio": "Certified Pilates instructor dengan fokus pada rehabilitation dan core strengthening. 6 tahun pengalaman mengajar.",
                "expertise": ["Pilates", "Rehabilitation", "Core Training"],
                "rating": 4.9,
                "verified": True,
                "image_url": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "username": "alex_zumba",
                "first_name": "Alexander",
                "last_name": "Rodriguez",
                "email": "alex.rodriguez@mamicoach.com",
                "bio": "Zumba instructor yang energik dengan passion untuk dance fitness. Membuat olahraga jadi menyenangkan dan tidak membosankan.",
                "expertise": ["Zumba", "Dance Fitness", "Cardio Dance"],
                "rating": 4.7,
                "verified": True,
                "image_url": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
            {
                "username": "lisa_swim",
                "first_name": "Lisa",
                "last_name": "Wang",
                "email": "lisa.wang@mamicoach.com",
                "bio": "Former competitive swimmer, sekarang mengajar teknik renang untuk pemula hingga advanced. Fokus pada teknik yang benar.",
                "expertise": ["Swimming", "Water Aerobics", "Technique Training"],
                "rating": 4.8,
                "verified": True,
                "image_url": "https://images.unsplash.com/photo-1489424731084-a5d8b219a5bb?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80",
            },
        ]

        for coach_data in coaches_data:
            # Create user if doesn't exist
            user, user_created = User.objects.get_or_create(
                username=coach_data["username"],
                defaults={
                    "first_name": coach_data["first_name"],
                    "last_name": coach_data["last_name"],
                    "email": coach_data["email"],
                },
            )

            if user_created:
                user.set_password("password123")  # Default password
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created user: {user.get_full_name()}")
                )

            # Create coach profile if doesn't exist
            coach_profile, coach_created = CoachProfile.objects.get_or_create(
                user=user,
                defaults={
                    "bio": coach_data["bio"],
                    "expertise": coach_data["expertise"],
                    "rating": coach_data["rating"],
                    "verified": coach_data["verified"],
                },
            )

            if coach_created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Created coach profile: {user.get_full_name()}"
                    )
                )

    def create_courses(self):
        """Create sample courses"""
        courses_data = [
            # Yoga Courses
            {
                "title": "Kelas Yoga Chi Space Studio",
                "description": "Kelas yoga untuk pemula dan menengah dengan fokus pada pernapasan dan postur. Cocok untuk yang ingin memulai perjalanan yoga atau memperdalam practice.",
                "location": "Jl. Kemang Raya No.7, Jakarta Selatan",
                "price": 300000,
                "duration": 90,
                "category": "Yoga",
                "coach": "sarah_yoga",
                "thumbnail_url": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Vinyasa Flow Yoga",
                "description": "Dynamic yoga class yang menggabungkan movement dan breath. Perfect untuk intermediate yogis yang ingin challenge.",
                "location": "Jl. Sudirman No.15, Jakarta Pusat",
                "price": 350000,
                "duration": 75,
                "category": "Yoga",
                "coach": "sarah_yoga",
                "thumbnail_url": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Pilates Courses
            {
                "title": "Pilates untuk Pemula",
                "description": "Kelas pilates dasar fokus pada core strengthening dan postur. Ideal untuk pemula yang ingin membangun foundation yang kuat.",
                "location": "Jl. Menteng Raya No.23, Jakarta Pusat",
                "price": 275000,
                "duration": 60,
                "category": "Pilates",
                "coach": "diana_pilates",
                "thumbnail_url": "https://images.unsplash.com/photo-1518611012118-696072aa579a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Advanced Pilates Reformer",
                "description": "Kelas pilates advanced menggunakan reformer machine. Untuk yang sudah berpengalaman dan ingin tantangan lebih.",
                "location": "Jl. Senayan No.8, Jakarta Selatan",
                "price": 450000,
                "duration": 75,
                "category": "Pilates",
                "coach": "diana_pilates",
                "thumbnail_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Strength Training Courses
            {
                "title": "Functional Strength Training",
                "description": "Latihan kekuatan fungsional untuk kehidupan sehari-hari. Menggunakan compound movements yang praktis dan efektif.",
                "location": "Jl. Gatot Subroto No.12, Jakarta Selatan",
                "price": 400000,
                "duration": 90,
                "category": "Strength Training",
                "coach": "mike_fitness",
                "thumbnail_url": "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "HIIT Cardio Blast",
                "description": "High-intensity interval training untuk membakar kalori maksimal dalam waktu singkat. Perfect untuk busy professionals.",
                "location": "Jl. Thamrin No.28, Jakarta Pusat",
                "price": 325000,
                "duration": 45,
                "category": "Cardio",
                "coach": "mike_fitness",
                "thumbnail_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Zumba Courses
            {
                "title": "Zumba Fitness Party",
                "description": "Dance fitness yang energik dan menyenangkan! Bakar kalori sambil bergoyang dengan musik Latin dan international hits.",
                "location": "Jl. Kuningan Raya No.45, Jakarta Selatan",
                "price": 250000,
                "duration": 60,
                "category": "Zumba",
                "coach": "alex_zumba",
                "thumbnail_url": "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Zumba Gold (55+)",
                "description": "Zumba yang dimodifikasi untuk usia 55+ dengan gerakan low-impact tapi tetap fun dan energik. Perfect untuk active seniors.",
                "location": "Jl. Radio Dalam No.17, Jakarta Selatan",
                "price": 200000,
                "duration": 45,
                "category": "Zumba",
                "coach": "alex_zumba",
                "thumbnail_url": "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Swimming Courses
            {
                "title": "Adult Swimming for Beginners",
                "description": "Belajar berenang dari nol untuk dewasa. Teknik dasar, safety, dan confidence building in water. Private atau small group.",
                "location": "Aquatic Center, Jl. Senayan No.99, Jakarta",
                "price": 500000,
                "duration": 60,
                "category": "Swimming",
                "coach": "lisa_swim",
                "thumbnail_url": "https://images.unsplash.com/photo-1544551763-46a013bb70d5?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Competitive Swimming Training",
                "description": "Advanced swimming technique dan conditioning untuk competitive swimmers atau yang ingin improve performance significantly.",
                "location": "Olympic Pool, Jl. Asia Afrika No.1, Jakarta",
                "price": 600000,
                "duration": 90,
                "category": "Swimming",
                "coach": "lisa_swim",
                "thumbnail_url": "https://images.unsplash.com/photo-1530549387789-4c1017266635?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Additional Yoga Courses
            {
                "title": "Prenatal Yoga",
                "description": "Gentle yoga practice yang aman untuk ibu hamil. Fokus pada pernapasan, relaksasi, dan persiapan persalinan.",
                "location": "Jl. Kebayoran Baru No.21, Jakarta Selatan",
                "price": 380000,
                "duration": 75,
                "category": "Yoga",
                "coach": "sarah_yoga",
                "thumbnail_url": "https://images.unsplash.com/photo-1599901860904-17e6ed7083a0?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Restorative Yoga",
                "description": "Gentle yoga untuk relaksasi mendalam menggunakan props. Perfect untuk stress relief dan recovery dari latihan intensif.",
                "location": "Jl. Pondok Indah No.33, Jakarta Selatan",
                "price": 320000,
                "duration": 90,
                "category": "Yoga",
                "coach": "sarah_yoga",
                "thumbnail_url": "https://images.unsplash.com/photo-1506126613408-eca07ce68773?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Additional Strength Training Courses
            {
                "title": "Olympic Weightlifting Basics",
                "description": "Belajar teknik dasar Olympic lifts (snatch & clean and jerk) dengan proper form dan safety. For intermediate to advanced.",
                "location": "Jl. Permata Hijau No.44, Jakarta Selatan",
                "price": 550000,
                "duration": 120,
                "category": "Strength Training",
                "coach": "mike_fitness",
                "thumbnail_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Powerlifting for Beginners",
                "description": "Squat, bench press, dan deadlift technique untuk pemula. Build strength foundation dengan proper form dan progressive overload.",
                "location": "Jl. Cilandak No.67, Jakarta Selatan",
                "price": 425000,
                "duration": 90,
                "category": "Strength Training",
                "coach": "mike_fitness",
                "thumbnail_url": "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Additional Cardio Courses
            {
                "title": "Tabata Extreme",
                "description": "4-minute high-intensity Tabata protocol untuk maximum fat burn. Short but extremely effective workout session.",
                "location": "Jl. Blok M No.89, Jakarta Selatan",
                "price": 200000,
                "duration": 30,
                "category": "Cardio",
                "coach": "mike_fitness",
                "thumbnail_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Boxing Cardio",
                "description": "Boxing-inspired cardio workout tanpa contact. Kombinasi jabs, hooks, dan footwork untuk full-body conditioning.",
                "location": "Jl. Kelapa Gading No.55, Jakarta Utara",
                "price": 350000,
                "duration": 60,
                "category": "Cardio",
                "coach": "alex_zumba",
                "thumbnail_url": "https://images.unsplash.com/photo-1549719386-74dfcbf7dbed?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Additional Pilates Courses
            {
                "title": "Pilates Mat Class",
                "description": "Classic Pilates mat exercises tanpa equipment. Fokus pada core, flexibility, dan body awareness. All levels welcome.",
                "location": "Jl. Mampang No.76, Jakarta Selatan",
                "price": 250000,
                "duration": 60,
                "category": "Pilates",
                "coach": "diana_pilates",
                "thumbnail_url": "https://images.unsplash.com/photo-1518611012118-696072aa579a?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Pilates for Back Pain",
                "description": "Therapeutic Pilates untuk mengatasi back pain dan improve posture. Gentle movements dengan focus pada spinal alignment.",
                "location": "Jl. Fatmawati No.38, Jakarta Selatan",
                "price": 400000,
                "duration": 75,
                "category": "Pilates",
                "coach": "diana_pilates",
                "thumbnail_url": "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Additional Zumba Courses
            {
                "title": "Zumba Toning",
                "description": "Zumba dengan light weights untuk toning dan sculpting. Kombinasi dance moves dengan resistance training yang fun.",
                "location": "Jl. Cipete No.92, Jakarta Selatan",
                "price": 280000,
                "duration": 60,
                "category": "Zumba",
                "coach": "alex_zumba",
                "thumbnail_url": "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Aqua Zumba",
                "description": "Zumba in the pool! Low-impact water workout yang gentle on joints tapi tetap memberikan great cardio dan resistance training.",
                "location": "Pool Club, Jl. Pantai Indah No.15, Jakarta Utara",
                "price": 320000,
                "duration": 45,
                "category": "Zumba",
                "coach": "alex_zumba",
                "thumbnail_url": "https://images.unsplash.com/photo-1571902943202-507ec2618e8f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            # Additional Swimming Courses
            {
                "title": "Water Aerobics",
                "description": "Low-impact aerobic exercise di air yang sempurna untuk senior atau recovery dari injury. Fun dan effective workout.",
                "location": "Jl. Kemayoran No.44, Jakarta Pusat",
                "price": 280000,
                "duration": 45,
                "category": "Swimming",
                "coach": "lisa_swim",
                "thumbnail_url": "https://images.unsplash.com/photo-1571902943202-507ec2618e8f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
            {
                "title": "Kids Swimming Lessons",
                "description": "Swimming lessons untuk anak usia 6-12 tahun. Basic water safety, floating, dan stroke technique dengan approach yang fun.",
                "location": "Family Pool, Jl. Bintaro No.88, Jakarta Selatan",
                "price": 350000,
                "duration": 45,
                "category": "Swimming",
                "coach": "lisa_swim",
                "thumbnail_url": "https://images.unsplash.com/photo-1594736797933-d0401ba2fe65?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80",
            },
        ]

        for course_data in courses_data:
            # Get category and coach
            try:
                category = Category.objects.get(name=course_data["category"])
                coach_user = User.objects.get(username=course_data["coach"])
                coach_profile = CoachProfile.objects.get(user=coach_user)

                course, created = Course.objects.get_or_create(
                    title=course_data["title"],
                    defaults={
                        "description": course_data["description"],
                        "location": course_data["location"],
                        "price": course_data["price"],
                        "duration": course_data["duration"],
                        "category": category,
                        "coach": coach_profile,
                        "thumbnail_url": course_data["thumbnail_url"],
                    },
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Created course: {course.title}")
                    )

            except (
                Category.DoesNotExist,
                User.DoesNotExist,
                CoachProfile.DoesNotExist,
            ) as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Error creating course {course_data['title']}: {e}"
                    )
                )
