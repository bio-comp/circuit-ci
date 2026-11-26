#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
testdir=$(mktemp -d)
trap 'rm -rf "$testdir"' EXIT
python3 - "$testdir/fixture.bin" <<'PYTHON'
from binascii import crc_hqx
from pathlib import Path
import sys

# Synthetic layout with independent CPython CRC calculation. No module capture.
base = bytearray(256)
fields = {0: 0x23, 1: 0x11, 2: 0x0c, 3: 3, 4: 4, 12: 1, 13: 3, 18: 7, 125: 214, 128: 0x2b}
for offset, value in fields.items():
    base[offset] = value
for start in (0, 128):
    crc = crc_hqx(base[start:start + 126], 0)
    base[start + 126:start + 128] = crc.to_bytes(2, "little")
upper = bytearray(256)
upper[73:93] = b"TEST-SODIMM".ljust(20,b" ")
Path(sys.argv[1]).write_bytes(base + upper)
PYTHON
"${CXX:-c++}" -std=c++17 -Wall -Wextra -Werror -pedantic check.cpp -o "$testdir/check"
"$testdir/check" "$testdir/fixture.bin"
