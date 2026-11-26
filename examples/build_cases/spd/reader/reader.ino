#include <Arduino.h>
#include <U8x8lib.h>
#include "spd.hpp"

// Independent software I2C OLED on D7(clock)/D6(data), powered from 3V3.
// Separate open-drain SPD bus on D4(data)/D5(clock).
U8X8_SSD1306_128X64_NONAME_SW_I2C oled(D7, D6, U8X8_PIN_NONE);
struct ArduinoPins {
    void sda(bool release) { digitalWrite(D4,release ? HIGH : LOW); }
    void scl(bool release) { digitalWrite(D5,release ? HIGH : LOW); }
    bool data_level() { return digitalRead(D4)==HIGH; }
    bool clock_level() { return digitalRead(D5)==HIGH; }
    uint32_t time_us() { return micros(); }
    void half_period() { delayMicroseconds(6); }
} pins;
spd::SerialBus<ArduinoPins> spd_bus(pins);
uint8_t raw[512];
spd::Info info;
spd::Status state;
unsigned page = 0;
bool lastButton = false;
unsigned long changedAt = 0;

void row(int n, const char* text) {
    char line[17];
    snprintf(line, sizeof(line), "%-16.16s", text);
    oled.drawString(0, n, line);
}
void paint() {
    oled.clearDisplay();
    row(0, "DDR4 SPD READER");
    row(7, "DRAM: UNTESTED");
    if (state != spd::Status::ok) {
        row(2, spd::message(state)); row(4, "Unplug to swap"); return;
    }
    char buf[32];
    if (page == 0) {
        snprintf(buf, sizeof(buf), "%lu MiB %uRx%u", static_cast<unsigned long>(info.mib), info.ranks, info.device_width);
        row(1,buf); snprintf(buf,sizeof(buf),"~%u MT/s SPD", info.rate); row(2,buf);
        snprintf(buf,sizeof(buf),"tCK %u ps",info.tck_ps);row(3,buf);
        row(4,"CRC base+mod OK");row(5,"2 reads agree");row(6,"Press: identity");
    } else {
        const bool hasPart = info.part[0] && !strchr(info.part,'?');
        row(1,hasPart ? info.part : "Part unavailable");
        row(2,hasPart && strlen(info.part)>16 ? info.part+16 : "IDs below: raw");
        snprintf(buf,sizeof(buf),"Mod ID %02X %02X",raw[320],raw[321]);row(3,buf);
        snprintf(buf,sizeof(buf),"IC  ID %02X %02X",raw[350],raw[351]);row(4,buf);
        snprintf(buf,sizeof(buf),"SN %02X%02X%02X%02X",raw[325],raw[326],raw[327],raw[328]);row(5,buf);
        row(6,info.temp_declared ? "TS: declared" : "TS: unflagged");
    }
}
void setup() {
    pinMode(D2,INPUT_PULLUP);
    oled.setI2CAddress(0x3c << 1);
    oled.begin(); oled.setFont(u8x8_font_chroma48medium8_r);
    row(0,"Reading SPD..."); row(7,"DRAM: UNTESTED");
    delay(100);
    pins.sda(true); pins.scl(true);
    pinMode(D4,OUTPUT_OPEN_DRAIN); pinMode(D5,OUTPUT_OPEN_DRAIN);
    pins.sda(true); pins.scl(true);
    state=spd::inspect(spd_bus,raw,info);
    paint();
}
void loop() {
    const bool down = digitalRead(D2) == LOW;
    if (down != lastButton && millis()-changedAt >= 40) {
        lastButton=down; changedAt=millis();
        if (down && state==spd::Status::ok) {page ^= 1u; paint();}
    }
    delay(10);
}
