#!/bin/sh
set -e

echo "Starting PyFlow Container Entrypoint Script..."

# Use .env.docker configuration inside container
if [ -f .env.docker ]; then
    cp .env.docker .env
    echo "Copied .env.docker to .env"
fi

# Run database readiness check
python wait_for_db.py db 3306

# Run database migrations
echo "Running database migrations..."
export PYTHONIOENCODING="utf-8"
python migrate.py

# Run database seeders (handles default admin and settings if not already seeded)
echo "Running database seeders..."
python -c "import sys; sys.path.insert(0, '.'); from core.database import Database; from config.config import get_config; Database.init(get_config()); from core.seeder import Seeder; Seeder.run_all(); Database.close()"

# Execute the container's main command
echo "Starting service command: $@"
exec "$@"
