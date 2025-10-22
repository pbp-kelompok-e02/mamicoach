from django.core.management.base import BaseCommand
from courses_and_coach.models import Category


class Command(BaseCommand):
    help = "Create sample categories for courses"

    def handle(self, *args, **options):
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
                    self.style.SUCCESS(
                        f"Successfully created category: {category.name}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Category already exists: {category.name}")
                )

        self.stdout.write(self.style.SUCCESS("Successfully populated categories!"))
