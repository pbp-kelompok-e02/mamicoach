"""
Management command to seed categories with thumbnails.
This should be run BEFORE crawling to ensure categories exist.
"""
from django.core.management.base import BaseCommand
from courses_and_coach.models import Category


class Command(BaseCommand):
    help = "Seed categories with predefined thumbnails. Run this before crawling data."

    def handle(self, *args, **options):
        categories_data = [
            {
                "name": "Golf",
                "description": "Latihan golf untuk meningkatkan teknik swing dan putting",
                "thumbnail_url": "https://res.cloudinary.com/dbqczwmdy/image/upload/v1761310501/Untitled_design.zip_-_8_aocr5p.png",
            },
            {
                "name": "Yoga",
                "description": "Latihan yoga untuk fleksibilitas dan ketenangan pikiran",
                "thumbnail_url": "https://res.cloudinary.com/dbqczwmdy/image/upload/v1761310501/Untitled_design.zip_-_7_avopan.png",
            },
            {
                "name": "Tenis Meja",
                "description": "Latihan tenis meja untuk meningkatkan refleks dan koordinasi",
                "thumbnail_url": "https://res.cloudinary.com/dbqczwmdy/image/upload/v1761310502/Untitled_design.zip_-_5_x65da6.png",
            },
            {
                "name": "Badminton",
                "description": "Latihan badminton untuk meningkatkan kecepatan dan stamina",
                "thumbnail_url": "https://res.cloudinary.com/dbqczwmdy/image/upload/v1761310501/Untitled_design.zip_-_3_if7wy4.png",
            },
            {
                "name": "Basket",
                "description": "Latihan basket untuk meningkatkan dribbling dan shooting",
                "thumbnail_url": "https://res.cloudinary.com/dbqczwmdy/image/upload/v1761310502/Untitled_design.zip_-_4_jhrmiv.png",
            },
            {
                "name": "Berenang",
                "description": "Latihan renang untuk seluruh tubuh",
                "thumbnail_url": "https://res.cloudinary.com/dbqczwmdy/image/upload/v1761310502/Untitled_design.zip_-_6_bh2rfg.png",
            },
            {
                "name": "Sepakbola",
                "description": "Latihan sepakbola untuk meningkatkan teknik dan teamwork",
                "thumbnail_url": "https://res.cloudinary.com/dbqczwmdy/image/upload/v1761310503/Untitled_design.zip_-_2_eriuui.png",
            },
            {
                "name": "Fitness",
                "description": "Latihan fitness untuk kesehatan dan kebugaran tubuh",
                "thumbnail_url": "https://res.cloudinary.com/dbqczwmdy/image/upload/v1761310503/Untitled_design.zip_-_9_r4dg9n.png",
            },
        ]

        created_count = 0
        updated_count = 0

        for cat_data in categories_data:
            category, created = Category.objects.update_or_create(
                name=cat_data["name"],
                defaults={
                    "description": cat_data["description"],
                    "thumbnail_url": cat_data["thumbnail_url"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Created category: {category.name}")
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f"↻ Updated category: {category.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nCategory seeding complete! Created: {created_count}, Updated: {updated_count}"
            )
        )
