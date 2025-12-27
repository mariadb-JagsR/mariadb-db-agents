#!/bin/bash
# Quick script to update .env file with new database credentials

cd "$(dirname "$0")"

# Backup existing .env
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "Backed up existing .env file"
fi

# Update or add database configuration
# Remove old DB_* lines and add new ones
if [ -f .env ]; then
    # Remove old DB configuration lines
    sed -i.bak '/^DB_HOST=/d; /^DB_PORT=/d; /^DB_USER=/d; /^DB_PASSWORD=/d; /^DB_DATABASE=/d' .env
    rm -f .env.bak
fi

# Add new database configuration
cat >> .env << 'EOF'

# Database Configuration (Updated)
DB_HOST=dbpgp29990659.sysp0000.db2.skysql.com
DB_PORT=3306
DB_USER=dbpgp29990659
DB_PASSWORD=aMWXUTkE3FYX!5rqCr3Lspghe
DB_DATABASE=mysql
EOF

echo "✅ Updated .env file with new database credentials"
echo ""
echo "New configuration:"
echo "  Host: dbpgp29990659.sysp0000.db2.skysql.com"
echo "  User: dbpgp29990659"
echo "  SSL: Enabled with certificate verification"
echo ""
echo "Test connection with:"
echo "  python -c \"from common.config import DBConfig; from common.db_client import run_readonly_query; cfg = DBConfig.from_env(); result = run_readonly_query('SELECT 1 as test'); print('✅ Connection successful!', result)\""


