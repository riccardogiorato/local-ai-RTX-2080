#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 -c "import socket; socket.create_connection(('127.0.0.1', 8912), timeout=2)" \
  || { echo "decryptor not running (did the runner source service.rc?)"; exit 1; }
python3 tests/test_outputs.py
