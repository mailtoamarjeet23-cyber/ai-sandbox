#!/bin/bash
set -e

# Migrations and seed data run automatically on app startup via SeedData.EnsurePopulated()

echo "[eshop] Running unit tests..."
# dotnet vstest runs directly against the compiled DLL — avoids a .NET 10 quirk where
# 'dotnet test --no-build' silently swallows all console output
TESTDLL=$(find /app/tests/UnitTests/bin/Release -name "UnitTests.dll" | head -1)
dotnet vstest "$TESTDLL" \
  --logger:"trx;LogFileName=/output/eshop_unit_tests.trx" \
  --logger:"console;verbosity=normal" \
  2>&1 | tee /output/eshop_tests.log || true

echo "[eshop] Starting web application (seed data loads on first startup)..."
# cd to DLL directory so ASP.NET Core content root resolves appsettings.json correctly
WEBDLL=$(find /app/src/Web/bin/Release -name "Web.dll" | head -1)
cd "$(dirname "$WEBDLL")"
exec dotnet "$(basename "$WEBDLL")"
