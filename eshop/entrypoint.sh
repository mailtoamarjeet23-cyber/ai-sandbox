#!/bin/bash
set -e

echo "[eshop] Running EF Core migrations..."
dotnet ef database update \
  --context CatalogContext \
  --project src/Infrastructure \
  --startup-project src/Web \
  --no-build \
  --configuration Release

dotnet ef database update \
  --context AppIdentityDbContext \
  --project src/Infrastructure \
  --startup-project src/Web \
  --no-build \
  --configuration Release

echo "[eshop] Running unit tests..."
dotnet test tests/UnitTests/UnitTests.csproj \
  --no-build \
  --configuration Release \
  --logger "trx;LogFileName=/output/eshop_unit_tests.trx" \
  --logger "console;verbosity=normal" \
  2>&1 | tee /output/eshop_tests.log

echo "[eshop] Starting web application (seed data loads on first startup)..."
exec dotnet src/Web/bin/Release/net8.0/Web.dll
