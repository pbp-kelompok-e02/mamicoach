#!/bin/sh
set -e

# These defaults make local "docker run" work out-of-the-box.
# For production (multiple replicas), you may want to disable auto-migrate:
#   RUN_MIGRATIONS=0 RUN_COLLECTSTATIC=0

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  python manage.py migrate --noinput
fi

if [ "${RUN_COLLECTSTATIC:-1}" = "1" ]; then
  python manage.py collectstatic --noinput
fi

exec "$@"
