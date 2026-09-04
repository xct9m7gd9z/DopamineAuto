#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

curl --fail --location --retry 3 --retry-delay 2 \
  https://apt.procurs.us/bootstraps/1800/bootstrap-iphoneos-arm64.tar.zst \
  --output bootstrap_1800.tar.zst
curl --fail --location --retry 3 --retry-delay 2 \
  https://apt.procurs.us/bootstraps/1900/bootstrap-iphoneos-arm64.tar.zst \
  --output bootstrap_1900.tar.zst

shasum -a 256 -c bootstrap-sha256sums.txt
