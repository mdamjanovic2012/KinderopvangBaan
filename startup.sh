#!/bin/bash
set -e

# Install GDAL/GEOS system libraries if not present
if ! find /usr/lib -name "libgdal.so*" 2>/dev/null | grep -q .; then
    echo "Installing GDAL/GEOS..."
    apt-get update -qq && apt-get install -y -q libgdal-dev libgeos-dev
fi

# Find actual library paths (versioned filenames like libgdal.so.30)
GDAL_SO=$(find /usr/lib -name "libgdal.so*" ! -name "*.la" 2>/dev/null | head -1)
GEOS_SO=$(find /usr/lib -name "libgeos_c.so*" ! -name "*.la" 2>/dev/null | head -1)

if [ -n "$GDAL_SO" ]; then
    export GDAL_LIBRARY_PATH="$GDAL_SO"
fi
if [ -n "$GEOS_SO" ]; then
    export GEOS_LIBRARY_PATH="$GEOS_SO"
fi

echo "GDAL: $GDAL_LIBRARY_PATH"
echo "GEOS: $GEOS_LIBRARY_PATH"

cd backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput

gunicorn --bind=0.0.0.0:8000 --timeout=120 --workers=2 config.wsgi
