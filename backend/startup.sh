#!/bin/bash
set -e

# Find GDAL/GEOS libraries dynamically on Azure App Service
GDAL_SO=$(find /usr/lib -name "libgdal.so*" 2>/dev/null | head -1)
GEOS_SO=$(find /usr/lib -name "libgeos_c.so*" 2>/dev/null | head -1)

if [ -n "$GDAL_SO" ]; then
    export GDAL_LIBRARY_PATH="$GDAL_SO"
fi
if [ -n "$GEOS_SO" ]; then
    export GEOS_LIBRARY_PATH="$GEOS_SO"
fi

echo "GDAL: $GDAL_LIBRARY_PATH"
echo "GEOS: $GEOS_LIBRARY_PATH"

# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Achtergrondtaken — ingebouwde throttling, blokkeren gunicorn niet
(python manage.py enrich_from_lrk || true) &    # max 1x per 30 dagen
(python manage.py backup_db || true) &            # max 1x per 7 dagen
(python manage.py update_diplomas || true) &      # max 1x per 180 dagen

# Start gunicorn
gunicorn --bind=0.0.0.0:8000 --timeout=120 --workers=2 config.wsgi
