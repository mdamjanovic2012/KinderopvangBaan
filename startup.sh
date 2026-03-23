#!/bin/bash
set -e

GDAL_CACHE="/home/gdal-cache"

if [ ! -f "$GDAL_CACHE/.installed_v2" ]; then
    echo "Installing GDAL/GEOS runtime (first run)..."
    # Install runtime only (much smaller/faster than -dev)
    apt-get update -qq && apt-get install -y -q libgdal28 libgeos-c1v5

    mkdir -p "$GDAL_CACHE"

    # Copy libgdal + libgeos + ALL transitive .so dependencies
    MAIN_LIBS=$(find /usr/lib -name "libgdal.so*" -o -name "libgeos_c.so*" -o -name "libgeos.so*" 2>/dev/null | grep -v "\.la$")
    ALL_DEPS=""
    for lib in $MAIN_LIBS; do
        DEPS=$(ldd "$lib" 2>/dev/null | grep "=> /" | awk '{print $3}')
        ALL_DEPS="$ALL_DEPS $DEPS $lib"
    done

    for lib in $ALL_DEPS; do
        [ -f "$lib" ] && cp "$lib" "$GDAL_CACHE/" 2>/dev/null || true
    done

    touch "$GDAL_CACHE/.installed_v2"
    echo "GDAL cached: $(ls $GDAL_CACHE | wc -l) files"
else
    echo "Using cached GDAL from $GDAL_CACHE"
fi

# Add cache dir to linker search path so all deps are found
export LD_LIBRARY_PATH="$GDAL_CACHE:${LD_LIBRARY_PATH:-}"

GDAL_SO=$(find "$GDAL_CACHE" -name "libgdal.so*" ! -name "*.la" ! -name "*.py" 2>/dev/null | head -1)
GEOS_SO=$(find "$GDAL_CACHE" -name "libgeos_c.so*" ! -name "*.la" 2>/dev/null | head -1)

if [ -n "$GDAL_SO" ]; then export GDAL_LIBRARY_PATH="$GDAL_SO"; fi
if [ -n "$GEOS_SO" ]; then export GEOS_LIBRARY_PATH="$GEOS_SO"; fi

echo "GDAL: $GDAL_LIBRARY_PATH"
echo "GEOS: $GEOS_LIBRARY_PATH"

cd backend
python manage.py migrate --noinput
python manage.py collectstatic --noinput

gunicorn --bind=0.0.0.0:8000 --timeout=120 --workers=2 config.wsgi
