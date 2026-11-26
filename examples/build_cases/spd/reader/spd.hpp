#pragma once
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "ee1004.hpp"

namespace spd {
enum class Status {
    ok, length, type, revision, layout, base_crc, module_crc, organization,
    timing, page_select, short_read, page_alias, unstable
};
inline const char* message(Status s) {
    switch (s) {
        case Status::ok: return "SPD fields read";
        case Status::length: return "Length error";
        case Status::type: return "Other module type";
        case Status::revision: return "Unsupported rev";
        case Status::layout: return "Unsupported layout";
        case Status::base_crc: return "Base CRC error";
        case Status::module_crc: return "Module CRC error";
        case Status::organization: return "Unsupported org";
        case Status::timing: return "Unsupported time";
        case Status::page_select: return "Page select error";
        case Status::short_read: return "Read failed";
        case Status::page_alias: return "Page alias";
        case Status::unstable: return "Reads disagree";
    }
    return "Unknown error";
}
struct Info {
    uint32_t mib = 0;
    uint16_t tck_ps = 0;
    uint16_t rate = 0;
    uint8_t device_width = 0, ranks = 0, bus_width = 0;
    bool temp_declared = false;
    char part[21]{};
};
inline uint16_t crc16(const uint8_t* data, size_t len) {
    uint16_t crc = 0;
    for (size_t i = 0; i < len; ++i) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = static_cast<uint16_t>((crc & 0x8000) ? (crc << 1) ^ 0x1021 : crc << 1);
    }
    return crc;
}
inline bool crc_matches(const uint8_t* block) {
    return crc16(block, 126) == (block[126] | (static_cast<uint16_t>(block[127]) << 8));
}
// Compact documented subset: SPD 1.1, 64-bit, nonhybrid, unbuffered,
// symmetric monolithic SO-DIMM with 1 or 2 ranks, x8 or x16 SDRAM.
inline Status decode(const uint8_t* raw, size_t length, Info& result) {
    result = {};
    if (length != 512) return Status::length;
    if (!crc_matches(raw)) return Status::base_crc;
    if (raw[2] != 0x0c || raw[3] != 0x03) return Status::type;
    if (raw[1] != 0x11) return Status::revision;
    if (raw[0] != 0x23 && raw[0] != 0x24) return Status::layout;
    if (!crc_matches(raw + 128)) return Status::module_crc;
    const unsigned density = raw[4] & 15;
    const unsigned org = raw[12];
    const unsigned width_code = org & 7;
    if (density > 6 || raw[6] != 0 || raw[13] != 3 || (org & 0xf0) != 0 ||
        (width_code != 1 && width_code != 2)) return Status::organization;
    const int fine = raw[125] < 128 ? raw[125] : static_cast<int>(raw[125]) - 256;
    const int tck = raw[18] * 125 + fine;
    // V1 intentionally limits the advertised clock-period range to DDR4-1600..3200.
    if (raw[17] != 0 || raw[18] == 0 || tck < 625 || tck > 1250) return Status::timing;
    Info parsed{};
    parsed.device_width = static_cast<uint8_t>(4u << width_code);
    parsed.ranks = static_cast<uint8_t>(((org >> 3) & 1) + 1);
    parsed.bus_width = 64;
    parsed.mib = ((256u << density) / 8u) * (64u / parsed.device_width) * parsed.ranks;
    parsed.tck_ps = static_cast<uint16_t>(tck);
    parsed.rate = static_cast<uint16_t>((2000000u + tck / 2u) / static_cast<unsigned>(tck));
    parsed.temp_declared = (raw[14] & 0x80) != 0;
    for (size_t i = 0; i < 20; ++i) {
        const uint8_t c = raw[329 + i];
        parsed.part[i] = (c >= 32 && c <= 126) ? static_cast<char>(c) : '?';
    }
    for (int i = 19; i >= 0 && parsed.part[i] == ' '; --i) parsed.part[i] = 0;
    result = parsed;
    return Status::ok;
}
template<class WireBus> Status read_image(WireBus& bus, uint8_t (&out)[512]) {
    for (uint8_t page = 0; page < 2; ++page) {
        if (!select_page(bus,page)) return Status::page_select;
        for (size_t offset=0; offset<256; offset+=16) {
            if (!read_chunk(bus, static_cast<uint8_t>(offset), out + page*256 + offset))
                return Status::short_read;
        }
    }
    if (memcmp(out, out + 256, 256) == 0) return Status::page_alias;
    return Status::ok;
}
template<class WireBus> Status inspect(WireBus& bus, uint8_t (&first)[512], Info& info) {
    info = {};
    uint8_t second[512]{};
    Status s = read_image(bus, first);
    if (s != Status::ok) return s;
    s = read_image(bus, second);
    if (s != Status::ok) return s;
    if (memcmp(first, second, sizeof(second)) != 0) return Status::unstable;
    return decode(first, sizeof(first), info);
}
}
