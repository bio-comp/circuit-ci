#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
tempdir=$(mktemp -d)
trap 'rm -rf "$tempdir"' EXIT
"${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror -pedantic companion/tests/check_report.cpp -o "$tempdir/check_report"
"$tempdir/check_report"
bash spd/tests/run.sh
(cd companion && node tests/check_setup.mjs)
