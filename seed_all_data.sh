#!/bin/bash
# Script to seed all categories and crawl data from Superprof
# Usage: ./seed_all_data.sh
# Make sure to activate your virtual environment first!

set -e  # Exit on error

echo "Starting MamiCoach Data Seeding..."
echo ""

# Step 1: Seed categories
echo "Step 1: Seeding categories..."
python3 manage.py seed_categories
echo ""

# Step 2: Crawl data for each category
echo "Step 2: Crawling data from Superprof..."
echo ""

# Golf
echo "Crawling Golf courses..."
python3 manage.py crawl_superprof --url "https://www.superprof.co.id/a/search/?type=3&adress=Indonesia&matiere=Golf&place[]=at_my_place&place[]=i_move&distance=200&webcam_from=in_pays&order_by=pertinence_DESC&price=all&first_lesson=all&response_time=all&is_mobile=2&pmin=1&pmax=3000001&isV=0&page=1" --category "Golf" \
  --sleep 1.5
echo ""

# Yoga
echo "Crawling Yoga courses..."
python3 manage.py crawl_superprof --url "https://www.superprof.co.id/a/search/?type=3&adress=Indonesia&matiere=Yoga&place[]=at_my_place&place[]=i_move&distance=200&webcam_from=in_pays&order_by=pertinence_DESC&price=all&first_lesson=all&response_time=all&is_mobile=2&pmin=1&pmax=3000001&isV=0&page=1" --category "Yoga"  --sleep 1.5
echo ""

# Tenis Meja
echo "Crawling Tenis Meja courses..."
python3 manage.py crawl_superprof \
  --url "https://www.superprof.co.id/a/search/?type=3&adress=Indonesia&matiere=Tenis%20Meja&place[]=at_my_place&place[]=i_move&distance=200&webcam_from=in_pays&order_by=pertinence_DESC&price=all&first_lesson=all&response_time=all&is_mobile=2&pmin=1&pmax=3000001&isV=0&page=1" \
  --category "Tenis Meja" \
  --sleep 1.5
echo ""

# Badminton
echo "Crawling Badminton courses..."
python3 manage.py crawl_superprof \
  --url "https://www.superprof.co.id/a/search/?type=3&adress=Indonesia&matiere=Badminton&place[]=at_my_place&place[]=i_move&distance=200&webcam_from=in_pays&order_by=pertinence_DESC&price=all&first_lesson=all&response_time=all&is_mobile=2&pmin=1&pmax=3000001&isV=0&page=1" \
  --category "Badminton" \
  --sleep 1.5
echo ""

# Basket
echo "Crawling Basket courses..."
python3 manage.py crawl_superprof \
  --url "https://www.superprof.co.id/a/search/?type=3&adress=Indonesia&matiere=Basket&place[]=at_my_place&place[]=i_move&distance=200&webcam_from=in_pays&order_by=pertinence_DESC&price=all&first_lesson=all&response_time=all&is_mobile=2&pmin=1&pmax=3000001&isV=0&page=1" \
  --category "Basket" \
  --sleep 1.5
echo ""

# Berenang
echo "Crawling Berenang courses..."
python3 manage.py crawl_superprof \
  --url "https://www.superprof.co.id/a/search/?type=3&adress=Indonesia&matiere=Berenang&place[]=at_my_place&place[]=i_move&distance=200&webcam_from=in_pays&order_by=pertinence_DESC&price=all&first_lesson=all&response_time=all&is_mobile=2&pmin=1&pmax=3000001&isV=0&page=1" \
  --category "Berenang" \
  --sleep 1.5
echo ""

# Sepakbola
echo "Crawling Sepakbola courses..."
python3 manage.py crawl_superprof \
  --url "https://www.superprof.co.id/a/search/?type=3&adress=Indonesia&id_matiere=148&matiere=Sepak%20bola&place[]=at_my_place&place[]=i_move&distance=200&webcam_from=in_pays&order_by=pertinence_DESC&price=all&first_lesson=all&response_time=all&is_mobile=2&pmin=1&pmax=3000001&isV=0&page=1" \
  --category "Sepakbola" \
  --sleep 1.5
echo ""

# Fitness
echo "Crawling Fitness courses..."
python3 manage.py crawl_superprof \
  --url "https://www.superprof.co.id/a/search/?type=3&adress=Indonesia&matiere=Fitness&place[]=at_my_place&place[]=i_move&distance=200&webcam_from=in_pays&order_by=pertinence_DESC&price=all&first_lesson=all&response_time=all&is_mobile=2&pmin=1&pmax=3000001&isV=0&page=1" \
  --category "Fitness" \
  --sleep 1.5
echo ""

echo "All data seeding complete!"
echo ""
echo "Summary:"
echo "--------"
python3 manage.py shell -c "
from courses_and_coach.models import Category, Course
from user_profile.models import CoachProfile
print(f'Categories: {Category.objects.count()}')
print(f'Coaches: {CoachProfile.objects.count()}')
print(f'Courses: {Course.objects.count()}')
print('')
for cat in Category.objects.all():
    print(f'  {cat.name}: {cat.courses.count()} courses')
"
