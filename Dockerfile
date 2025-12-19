# Multi-stage build for smaller image
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    jpeg-dev \
    zlib-dev \
    libffi-dev \
    openssl-dev

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-alpine AS runtime

WORKDIR /app

# Runtime dependencies (for psycopg2/Pillow/SSL)
RUN apk add --no-cache \
    libpq \
    jpeg-turbo \
    zlib \
    libffi \
    openssl

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy app
COPY . .

# Production setup
EXPOSE 80

# Django production server
CMD ["sh", "-c", "python manage.py migrate --noinput; WSGI_MODULE=$(python -c \"import glob; files = glob.glob('*/wsgi.py'); print(files[0].split('/')[0] if files else 'wsgi')\"); gunicorn --bind 0.0.0.0:80 --workers 2 $WSGI_MODULE.wsgi:application"]
