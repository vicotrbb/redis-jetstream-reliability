#!/bin/sh
# Dependency setup occurs before timing. Never weaken checksum verification.
set -eu
attempt=1
while ! go mod download; do
  if [ "$attempt" -ge 4 ]; then exit 1; fi
  attempt=$((attempt + 1))
  sleep 1
done
go mod verify
