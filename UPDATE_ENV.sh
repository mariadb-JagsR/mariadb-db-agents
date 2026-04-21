#!/bin/bash
# Append or refresh DB_* lines in .env from environment variables.
# Export secrets in your shell first — do not hard-code them in this file.
#
# Usage:
#   export DB_HOST="your-host.example.com"
#   export DB_PORT="3306"
#   export DB_USER="your_user"
#   export DB_PASSWORD="your_password"
#   export DB_DATABASE="mysql"
#   ./UPDATE_ENV.sh

set -euo pipefail
cd "$(dirname "$0")"

: "${DB_HOST:?Set DB_HOST}"
: "${DB_PORT:?Set DB_PORT}"
: "${DB_USER:?Set DB_USER}"
: "${DB_PASSWORD:?Set DB_PASSWORD}"
: "${DB_DATABASE:?Set DB_DATABASE}"

if [ -f .env ]; then
    cp .env ".env.backup.$(date +%Y%m%d_%H%M%S)"
    echo "Backed up existing .env"
    sed -i.bak '/^DB_HOST=/d; /^DB_PORT=/d; /^DB_USER=/d; /^DB_PASSWORD=/d; /^DB_DATABASE=/d' .env
    rm -f .env.bak
fi

{
    echo ""
    echo "# Database configuration (from UPDATE_ENV.sh — $(date -u +%Y-%m-%dT%H:%MZ))"
    echo "DB_HOST=${DB_HOST}"
    echo "DB_PORT=${DB_PORT}"
    echo "DB_USER=${DB_USER}"
    echo "DB_PASSWORD=${DB_PASSWORD}"
    echo "DB_DATABASE=${DB_DATABASE}"
} >> .env

echo "Updated .env DB_* keys (password not printed)."
echo "  Host: ${DB_HOST}"
echo "  User: ${DB_USER}"
echo "  SSL: enabled for SkySQL hosts (see db_client)"
