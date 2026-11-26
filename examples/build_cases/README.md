# Embedded build examples

Run commands from the repository root. These are source prototypes and synthetic
host tests for a network companion and a portable DDR4 SPD reader. All interfaces,
power, indication accuracy and enclosure behavior still need bench verification.

| Path under `examples/build_cases/` | Purpose |
| --- | --- |
| `companion/firmware/Lantern/` | ESP32-S3, local interface display, optional M5Stack U138 and Wi-Fi fallback |
| `spd/reader/` | Read-only identification of a supported DDR4 SO-DIMM via a dedicated SPD bus |
| `check-hosts.sh` | Synthetic C++17 modem-parser, SPD protocol, CRC and decoder tests |
| `replay.py` | Reproduce the legacy Circuit-CI reporter's treatment of 19 declared evidence gaps |

## Test the examples

```bash
bash examples/build_cases/check-hosts.sh
uv sync --locked
uv run --locked python examples/build_cases/replay.py
```

The first command needs Python 3, Bash, Node.js and a C++17 compiler. Set `CXX` to change
the compiler executable. The second workflow uses the repository lockfile.
On main `bb15beaaadab615c026784e2f67c9aa01ca53755` the replay exits 1:
all 19 inputs with declared prerequisites returned `AUTO_PASS`. The firmware
examples can be tested independently while the reporter contract evolves.

## Compile the network companion

[Build and onboarding](companion/firmware/BUILD.md) includes an isolated sketchbook,
the vendor commit and exact archive versions, board options, and the USB setup
procedure. The sketch targets Freenove FNK0104A/B (2.8-inch ILI9341) with the
Espressif core 3.2.0. Optional U138 firmware is queried over UART. Remove both
the U138 power and UART leads before connecting a computer. The device can run
the status and animation pages without network credentials. It does not request
Proxmox data. The USB setup page only sends credentials to the selected serial
device; its on-device settings are not encrypted by this example.

## Compile the SPD reader

The sketch targets Seeed XIAO ESP32-C5 and an SSD1306 128×64 OLED at address
0x3c. Use Arduino CLI 1.3.1, Espressif core 3.3.5 and U8g2 2.35.30 in an
isolated sketchbook, with the Espressif package index configured.

```bash
arduino-cli core install esp32:esp32@3.3.5
arduino-cli lib install U8g2@2.35.30
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C5 examples/build_cases/spd/reader
```

Inspect `reader.ino` for the two separate buses and button assignment. The example
requires one module on a qualified carrier. Connector orientation, VDDSPD under
load, return paths, pull-ups, level translation, ESD and power-off insertion need
separate qualification before connecting a DIMM. Running the host test needs none
of this hardware.

The reader's supported decode subset is DDR4 SPD 1.1, symmetric, monolithic,
64-bit unbuffered SO-DIMMs with one or two ranks and x8 or x16 chips. It reads
two 512-byte images, checks for short reads, aliasing and disagreement, and
checks the CRCs covering the base and module-specific fields. It never sends a
nonvolatile data write or write-protection command. Page selection and address
pointer transactions use I²C write direction on the wire. Manufacturer IDs and
module serial data on the second page do not have those CRCs. Declared timing
and capacity are metadata; there is no memory-cell read/write test.
