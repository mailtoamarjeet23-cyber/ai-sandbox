#!/bin/bash
set -e

echo "[medplum] Generating config from environment..."
cat > /app/medplum.config.json << EOF
{
  "port": 8103,
  "baseUrl": "http://localhost:8103/",
  "database": {
    "host": "${MEDPLUM_DATABASE_HOST}",
    "port": ${MEDPLUM_DATABASE_PORT:-5432},
    "dbname": "${MEDPLUM_DATABASE_DBNAME}",
    "username": "${MEDPLUM_DATABASE_USERNAME}",
    "password": "${MEDPLUM_DATABASE_PASSWORD}",
    "ssl": false
  },
  "redis": {
    "host": "${MEDPLUM_REDIS_HOST}",
    "port": ${MEDPLUM_REDIS_PORT:-6379}
  }
}
EOF

echo "[medplum] Starting server (migrations run automatically on start)..."
# 'file' tells the server to load medplum.config.json from the working directory
exec node packages/server/dist/index.js file:/app/medplum.config.json
