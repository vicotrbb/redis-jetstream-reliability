#!/bin/sh
# Execute only inside the homelab runner, after benchmark collection has ended.
set -eu
cd /work/formal
printf 'Verification UTC: '
date -u +%Y-%m-%dT%H:%M:%SZ
sha256sum DeliveryModel.lean
if [ ! -x lean-4.24.0-linux/bin/lean ]; then
  curl --fail --silent --show-error --location --retry 3 \
    https://github.com/leanprover/lean4/releases/download/v4.24.0/lean-4.24.0-linux.tar.zst \
    --output lean-4.24.0-linux.tar.zst
  printf '%s\n' 'b14f5e5159219dd1a1956c3b806813319f5e94ccd5bdfd56f54520609a5bb5ec  lean-4.24.0-linux.tar.zst' | sha256sum --check --strict
  if ! command -v zstd >/dev/null 2>&1; then
    apt-get update > dependency-install.log 2>&1
    apt-get install -y --no-install-recommends zstd >> dependency-install.log 2>&1
  fi
  zstd --version
  tar --zstd -xf lean-4.24.0-linux.tar.zst
fi
lean-4.24.0-linux/bin/lean --version
sha256sum lean-4.24.0-linux/bin/lean
lean-4.24.0-linux/bin/lean -DwarningAsError=true DeliveryModel.lean
