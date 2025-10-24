#!/bin/bash

# Delete all migration files from all Django apps in the project
# This script AUTOMATICALLY DETECTS all apps with migrations/ directories
# It only removes migration files (*.py) from migrations/ directories
# It preserves __init__.py files to keep the directories intact

# Change to script directory (Django project root)
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "Django Migrations Cleanup Script (Auto-Detect)"
echo "========================================"
echo ""
echo "Current directory: $(pwd)"
echo ""

# Counter for deleted files
DELETED=0

# Auto-detect all directories with migrations/ subdirectory
echo "Auto-detecting apps with migrations..."
echo ""

for app_dir in */; do
    app_name="${app_dir%/}"  # Remove trailing slash
    MIGRATIONS_DIR="$app_dir/migrations"
    
    if [ -d "$MIGRATIONS_DIR" ]; then
        echo "Cleaning migrations from: $app_name"
        
        # Delete all .py files except __init__.py
        for file in "$MIGRATIONS_DIR"/*.py; do
            if [ -f "$file" ]; then
                filename=$(basename "$file")
                if [ "$filename" != "__init__.py" ]; then
                    rm -f "$file"
                    ((DELETED++))
                    echo "  - Deleted: $filename"
                fi
            fi
        done
        
        # Remove __pycache__ directory entirely
        if [ -d "$MIGRATIONS_DIR/__pycache__" ]; then
            echo "  - Removing __pycache__ from $app_name/migrations"
            rm -rf "$MIGRATIONS_DIR/__pycache__"
        fi
        
        # Remove all .pyc files if any exist
        for file in "$MIGRATIONS_DIR"/*.pyc; do
            if [ -f "$file" ]; then
                rm -f "$file"
                ((DELETED++))
                filename=$(basename "$file")
                echo "  - Deleted: $filename"
            fi
        done
        echo ""
    fi
done

echo "========================================"
echo "Summary:"
echo "Total migration files deleted: $DELETED"
echo "========================================"
echo ""

# Ask if user wants to run makemigrations, migrate, and populate_all
read -p "Do you want to run makemigrations, migrate, and populate_all? (Y/N): " RUN_MIGRATIONS

if [[ "$RUN_MIGRATIONS" =~ ^[Yy]$ ]]; then
    echo ""
    echo "Running makemigrations..."
    python3 manage.py makemigrations
    
    echo ""
    echo "Running migrate..."
    python3 manage.py migrate
    
    echo ""
    echo "Running populate_all..."
    python3 manage.py populate_all --verbosity 2
    if [ $? -eq 0 ]; then
        echo ""
        echo "All done!"
    else
        echo ""
        echo "Error running populate_all. Check output above."
    fi
else
    echo ""
    echo "Next steps (run manually when ready):"
    echo "1. Run: python3 manage.py makemigrations"
    echo "2. Run: python3 manage.py migrate"
    echo "3. Run: python3 manage.py populate_all"
fi

echo ""
