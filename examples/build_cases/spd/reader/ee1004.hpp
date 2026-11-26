#pragma once
#include <stddef.h>
#include <stdint.h>

namespace spd {
enum class Reply { ack, nack, fault };

// Pins exposes open-drain release/pull-low only. True releases a line.
template<class Pins> class SerialBus {
    Pins& io;
    bool clock_high() {
        io.scl(true);
        const uint32_t started = io.time_us();
        while (!io.clock_level()) {
            if (uint32_t(io.time_us() - started) >= 2000) return false;
        }
        io.half_period();
        return true;
    }
    bool sample_bit(bool release, bool& observed) {
        io.sda(release); io.half_period();
        if (!clock_high()) return false;
        observed = io.data_level();
        io.scl(false);
        return true;
    }
public:
    explicit SerialBus(Pins& pins) : io(pins) {}
    bool start() {
        io.sda(true); io.half_period();
        if (!clock_high() || !io.data_level()) return false;
        io.sda(false); io.half_period(); io.scl(false);
        return true;
    }
    bool stop() {
        io.scl(false); io.sda(false); io.half_period();
        const bool clock_ok = clock_high();
        io.sda(true); io.half_period();
        return clock_ok && io.data_level();
    }
    Reply send(uint8_t byte) {
        bool sampled = false;
        for (uint8_t mask = 128; mask != 0; mask >>= 1) {
            const bool one = (byte & mask) != 0;
            if (!sample_bit(one, sampled) || sampled != one) return Reply::fault;
        }
        if (!sample_bit(true, sampled)) return Reply::fault;
        return sampled ? Reply::nack : Reply::ack;
    }
    bool receive(uint8_t& value, bool more) {
        value=0;
        bool sampled=false;
        for (unsigned i=0; i<8; ++i) {
            if (!sample_bit(true,sampled)) return false;
            value = static_cast<uint8_t>((value << 1) | (sampled ? 1 : 0));
        }
        return sample_bit(!more,sampled) && sampled == !more;
    }
};

template<class Bus> bool select_page(Bus& bus, uint8_t page) {
    // Only volatile page-control addresses 0x36/0x37; no protection commands.
    bool ok = bus.start() && bus.send(static_cast<uint8_t>(0x6c + 2*page)) == Reply::ack;
    // Microchip 34AA04 NACKs both dummy bytes; ST permits ACK or NACK.
    if (ok) ok = bus.send(0) != Reply::fault && bus.send(0) != Reply::fault;
    const bool ended = bus.stop();
    if (!ok || !ended) return false;
    if (!bus.start()) { bus.stop(); return false; }
    const Reply selection = bus.send(0x6d);  // RPA: ACK=page zero, NACK=page one
    uint8_t unused=0;
    // Microchip requires one dummy read followed by master NACK for either page.
    const bool clocked = selection != Reply::fault && bus.receive(unused, false);
    const bool closed = bus.stop();
    return selection == (page==0 ? Reply::ack : Reply::nack) && clocked && closed;
}

template<class Bus> bool read_chunk(Bus& bus, uint8_t offset, uint8_t* out) {
    // Pointer alone at 0x50(W), repeated START then 0x50(R). No EEPROM data write.
    bool ok=bus.start() && bus.send(0xa0)==Reply::ack && bus.send(offset)==Reply::ack &&
            bus.start() && bus.send(0xa1)==Reply::ack;
    for (unsigned i=0; ok && i<16; ++i)
        ok = bus.receive(out[i], i!=15);
    const bool ended=bus.stop();
    return ok && ended;
}
}
