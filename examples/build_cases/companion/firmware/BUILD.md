# LAN Lantern firmware

The target is the Freenove 2.8-inch ILI9341 A/B profile. Verify the board and run the Freenove display demo first. For the capacitive version, run its touch demo too. Unplug all U138 power and UART leads before connecting the PC. Use a USB data cable directly to the display. The screen works without a U138; it reports the absence of modem replies. A tap, a short BOOT press after startup, or USB command "next" turns the page.

## Compile

Use Arduino CLI 1.6.0, Espressif Arduino core 3.2.0 (the version used in Freenove’s tutorial), vendor-fork TFT_eSPI 2.5.43 and Freenove TFT_eSPI_Setups 1.3 at vendor commit 90004f874ed567b3c09d534d021172cb716e61a1. Use a project-specific sketchbook so the display profile does not override other sketches. From the directory containing this firmware directory, in Bash:

```sh
mkdir -p .lantern-build/sketchbook/libraries
build_root="$PWD/.lantern-build"
arduino-cli config init --dest-file "$build_root/arduino.yaml"
arduino-cli config set directories.user "$build_root/sketchbook" --config-file "$build_root/arduino.yaml"
arduino-cli config set directories.data "$build_root/packages" --config-file "$build_root/arduino.yaml"
arduino-cli config set board_manager.additional_urls https://espressif.github.io/arduino-esp32/package_esp32_index.json --config-file "$build_root/arduino.yaml"
cli=(arduino-cli --config-file "$build_root/arduino.yaml")
"${cli[@]}" core update-index
"${cli[@]}" core install esp32:esp32@3.2.0
git clone --filter=blob:none --no-checkout https://github.com/Freenove/Freenove_ESP32_S3_Display.git "$build_root/vendor"
pin=90004f874ed567b3c09d534d021172cb716e61a1
for lib in TFT_eSPI_v2.5.43 TFT_eSPI_Setups_v1.3; do
  git -C "$build_root/vendor" show "$pin:Libraries/FNK0104AB/$lib.zip" > "$build_root/$lib.zip"
  unzip -q "$build_root/$lib.zip" -d "$build_root/sketchbook/libraries"
done
board='esp32:esp32:esp32s3:CDCOnBoot=cdc,FlashSize=16M,PSRAM=opi'
"${cli[@]}" compile --fqbn "$board" --build-path "$build_root/out" firmware/Lantern
"${cli[@]}" board list
```

Select the serial device that appeared when this display was plugged in. On macOS it will often start with /dev/cu.usbmodem; on Linux, /dev/ttyACM. If needed hold BOOT, press and release RESET, then release BOOT. Use the port on your own screen in place of PORT below. This overwrites the board's current sketch. The manufacturer's Board Test / recovery demo is available in its repository. Compile was verified; uploading and panel behavior require the physical unit.

```sh
"${cli[@]}" upload -p PORT --fqbn "$board" --input-dir "$build_root/out" firmware/Lantern
```

## Use

- With no network or credentials, use the three pages for modem status, interface detail and night-watch animation. The sample strip has one cell every 2.5 s; green means an address was reported, amber means a complete modem report with no address, red means missing/unusable evidence. This animation does not depict network traffic.
- Factory configuration is wired UART at 9600 8N1. Only AT+CIPETH? is used by default. On a wired unit, intentionally hold BOOT for at least two seconds **after the unit has started**, then release to toggle a periodic echo to the currently reported gateway. Enable only on a permitted network. The setting survives power cycles. Read the result on page two. No confirmed echo can mean filtering, unsupported command, timeout or lost link.
- For Wi-Fi, disconnect both U138 power and data, connect the board to a computer over USB, close the Arduino serial monitor, and serve the setup page locally: `python3 -m http.server 8080 --bind 127.0.0.1 --directory firmware`. Open http://127.0.0.1:8080/setup.html in a Chromium desktop browser. Enter your own 2.4 GHz WPA personal SSID/passphrase, select Save Wi-Fi and choose the board serial port. Credentials travel over this local USB connection. The board stores them in local preferences. Flash encryption was not enabled or validated; assume someone holding it can extract them. A wrong password yields offline. Repeat setup to fix it.
- Choose **Use Ethernet** to switch back with saved Wi-Fi retained; **Erase saved Wi-Fi** clears the application preferences. Unplug USB before reconnecting the powered UART loom. USB setup and hardware controls also work when the touch overlay is absent. Close the local web server after setup.

## Reproduce offline checks

From the directory containing firmware and tests:

```sh
c++ -std=c++17 -Wall -Wextra -Werror tests/check_report.cpp -o /tmp/lantern-report && /tmp/lantern-report
node tests/check_setup.mjs
```

These exercise strict address parsing, incomplete/malformed reports, duplicate fields, rollover, ping timing, target change, timeout, and browser setup/erase over mock serial. Physically verify byte framing, timeout/recovery, upload method, rendering, touch, and cold boots on the delivered board. The source uses the upstream TFT interface; Freenove files and its artwork are not redistributed here.
