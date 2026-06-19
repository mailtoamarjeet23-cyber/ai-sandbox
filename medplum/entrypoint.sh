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

echo "[medplum] Starting server in background (migrations run on first start)..."
node /app/packages/server/dist/index.js file:/app/medplum.config.json &
SERVER_PID=$!

echo "[medplum] Waiting for server to become healthy..."
for i in $(seq 1 18); do
  if curl -sf http://localhost:8103/healthcheck > /dev/null 2>&1; then
    echo "[medplum] Server healthy after ~$((i * 5))s"
    break
  fi
  sleep 5
done

echo "[medplum] Running server tests (config and utility tests)..."
# Must run from packages/server — babel-jest transform and jest.config.json are resolved from <rootDir>
# Full test suite requires ~30 min; config/util tests are fast representative subset
cd /app/packages/server && NODE_ENV=test npx jest \
  --testPathPatterns="src/(config|util)" \
  --forceExit \
  --passWithNoTests \
  --testTimeout=15000 \
  --json --outputFile=/output/medplum_tests.json \
  2>&1 | tee /output/medplum_tests.log || true
cd /app

echo "[medplum] Tests complete. Server running in foreground..."
# Forward signals to the server process and wait for it to exit
trap "kill $SERVER_PID 2>/dev/null" SIGTERM SIGINT
wait $SERVER_PID
