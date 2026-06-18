#!/bin/bash
set -e

echo "Cleaning previous state..."
docker compose down -v

echo "Building and starting sandbox..."
docker compose up --build -d

echo "Waiting for databases to be healthy..."
for service in sqlserver postgres redis; do
  echo -n "  $service: "
  until [ "$(docker inspect --format='{{.State.Health.Status}}' $service 2>/dev/null)" = "healthy" ]; do
    echo -n "."
    sleep 3
  done
  echo " ready"
done

echo ""
echo "Sandbox is up."
echo ""
echo "Access:"
echo "  eShop:   http://localhost:5001"
echo "  Medplum: http://localhost:8103/healthcheck"
echo ""
echo "Structured test output:"
echo "  ./output/eshop_unit_tests.trx"
echo "  ./output/eshop_tests.log"
echo ""
echo "Useful commands:"
echo "  docker compose logs -f eshop"
echo "  docker compose logs -f medplum"
echo "  docker compose down -v    # clean reset"
