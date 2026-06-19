#!/bin/bash
set -e

# Migrations and seed data run automatically on app startup via SeedData.EnsurePopulated()

echo "[eshop] Running unit tests..."
dotnet test tests/UnitTests/ \
  --no-build \
  --configuration Release \
  --logger "trx;LogFileName=/output/eshop_unit_tests.trx" \
  --logger "console;verbosity=normal" \
  2>&1 | tee /output/eshop_tests.log

echo "[eshop] Starting web application (seed data loads on first startup)..."
# cd to DLL directory so ASP.NET Core content root resolves appsettings.json correctly
WEBDLL=$(find /app/src/Web/bin/Release -name "Web.dll" | head -1)
cd "$(dirname "$WEBDLL")"
exec dotnet "$(basename "$WEBDLL")"
