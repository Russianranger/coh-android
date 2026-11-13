#!/bin/bash
# pg_fixture.sh: start the runner's PostgreSQL 16 as the guest SQL tests' localhost fixture
# (database coh_test_startup_bundle, as the android-client workflows prepare it). Run by the
# ArmPort build before test_character_profile_eligibility.py with COH_REQUIRE_POSTGRESQL=1.
set -euo pipefail
sudo apt-get install -y --no-install-recommends postgresql-16 postgresql-client-16
sudo systemctl start postgresql 2>/dev/null || sudo pg_ctlcluster 16 main start || true
for _ in $(seq 1 30); do
  pg_isready --host 127.0.0.1 --port 5432 && break
  sleep 1
done
cd /
sudo -u postgres psql -X --dbname postgres --set ON_ERROR_STOP=1 \
  --command "ALTER ROLE postgres WITH LOGIN PASSWORD 'coh-host-fixture'"
sudo -u postgres createdb --owner postgres coh_test_startup_bundle
test "$(PGPASSWORD=coh-host-fixture psql -X --host 127.0.0.1 --port 5432 --username postgres \
  --dbname coh_test_startup_bundle --tuples-only --no-align \
  --command "SELECT current_setting('server_version_num')::integer / 10000")" = 16
