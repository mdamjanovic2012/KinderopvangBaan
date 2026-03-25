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

# LRK enrichment — runs at most once per 30 days (timestamp in /home/.lrk_last_run)
# Safe: only UPDATEs existing records, never deletes data
python manage.py enrich_from_lrk || echo "LRK enrichment skipped or failed (non-blocking)"

# Start gunicorn
gunicorn --bind=0.0.0.0:8000 --timeout=120 --workers=2 config.wsgi
