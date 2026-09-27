#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
python3 tests/test_outputs.py
