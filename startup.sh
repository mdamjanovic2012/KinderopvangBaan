#!/bin/bash
set -e

GDAL_CACHE="/home/gdal-cache"

# Install GDAL/GEOS only if not already cached
if [ ! -f "$GDAL_CACHE/libgdal.so" ]; then
    echo "Installing GDAL/GEOS (first run)..."
    apt-get update -qq && apt-get install -y -q libgdal-dev libgeos-dev

    # Cache to /home (persistent across container restarts)
    mkdir -p "$GDAL_CACHE"
    find /usr/lib -name "libgdal.so*" ! -name "*.la" -exec cp {} "$GDAL_CACHE/" \;
    find /usr/lib -name "libgeos_c.so*" ! -name "*.la" -exec cp {} "$GDAL_CACHE/" \;
    find /usr/lib -name "libgeos.so*" ! -name "*.la" -exec cp {} "$GDAL_CACHE/" \;
    echo "GDAL cached to $GDAL_CACHE"
else
    echo "GDAL already cached, copying from $GDAL_CACHE"
    cp "$GDAL_CACHE"/lib* /usr/lib/x86_64-linux-gnu/ 2>/dev/null || true
fi

# Find actual library paths
GDAL_SO=$(find /usr/lib "$GDAL_CACHE" -name "libgdal.so*" ! -name "*.la" 2>/dev/null | head -1)
GEOS_SO=$(find /usr/lib "$GDAL_CACHE" -name "libgeos_c.so*" ! -name "*.la" 2>/dev/null | head -1)

if [ -n "$GDAL_SO" ]; then export GDAL_LIBRARY_PATH="$GDAL_SO"; fi
if [ -n "$GEOS_SO" ]; then export GEOS_LIBRARY_PATH="$GEOS_SO"; fi

echo "GDAL: $GDAL_LIBRARY_PATH"
echo "GEOS: $GEOS_LIBRARY_PATH"

cd backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput

gunicorn --bind=0.0.0.0:8000 --timeout=120 --workers=2 config.wsgi
