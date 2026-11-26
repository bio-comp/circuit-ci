// The Arduino core defines bit(b) before loading the sketch headers.
#define bit(b) (1UL << (b))
#include "../reader/spd.hpp"
#undef bit
#include <algorithm>
#include <array>
#include <cassert>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

class FakeWire {
    enum class Mode { idle, address, selector, rpa, pointer, pointer_done, read };
    Mode mode = Mode::idle;
    unsigned page=0, offset=0, pending=0, length=0;
public:
    std::array<uint8_t,512> data{};
    unsigned count=0, selections=0, transfers=0, dummy_reads=0;
    bool fail_select{}, fail_pointer{}, short_read{}, ignore_page{}, mutate{}, dropped_byte{};
    bool wrong_rpa{}, dummy_nack{}, selector_fault{}, bad_stop{}, read_disappears{};
    bool start() {
        assert(mode==Mode::idle || mode==Mode::pointer_done);
        mode=Mode::address; return true;
    }
    spd::Reply send(uint8_t b) {
        using spd::Reply;
        if (mode==Mode::address) {
            switch (b) {
                case 0x6c: case 0x6e:
                    mode=Mode::selector; length=0; pending=(b-0x6cu)/2u;
                    assert(pending==selections%2); ++selections;
                    if(mutate && selections==3) data[400]^=1;
                    return fail_select ? Reply::nack : Reply::ack;
                case 0x6d: mode=Mode::rpa; return (page==0)!=wrong_rpa ? Reply::ack : Reply::nack;
                case 0xa0: mode=Mode::pointer; return read_disappears && page==1 ? Reply::nack : Reply::ack;
                case 0xa1: mode=Mode::read; length=0; ++transfers; return Reply::ack;
                default: assert(false); return Reply::fault;
            }
        }
        if (mode==Mode::selector) {
            assert(length<2 && b==0); ++length;
            if (selector_fault) return Reply::fault;
            return dummy_nack ? Reply::nack : Reply::ack;
        }
        assert(mode==Mode::pointer && b==16*(transfers%16));
        offset=b; mode=Mode::pointer_done;
        return fail_pointer ? Reply::nack : Reply::ack;
    }
    bool receive(uint8_t& out,bool more) {
        if (mode==Mode::rpa) {assert(!more); ++dummy_reads; out=0xff; return true;}
        assert(mode==Mode::read && length<16 && more==(length!=15));
        out=data.at((ignore_page ? 0 : page)*256+offset+length);
        ++length; ++count;
        return !(short_read && length==16) && !dropped_byte;
    }
    bool stop() {
        if (mode==Mode::selector && length==2) page=pending;
        mode=Mode::idle; return !bad_stop;
    }
};

struct StuckClock {
    uint32_t now=0;
    void sda(bool) {}
    void scl(bool) {}
    bool clock_level() {return false;}
    bool data_level() {return true;}
    uint32_t time_us() {return now++;}
    void half_period() {}
};

int main(int argc, char** argv) {
    assert(argc==2);
    FakeWire reference;
    std::ifstream f(argv[1],std::ios::binary);
    f.read(reinterpret_cast<char*>(reference.data.data()),512);
    assert(f.gcount()==512);
    spd::Info info;
    uint8_t image[512]{};
    assert(spd::inspect(reference,image,info)==spd::Status::ok);
    assert(reference.count==1024 && reference.transfers==64 && reference.selections==4 && reference.dummy_reads==4);
    assert(info.mib==4096 && info.device_width==8 && info.ranks==1 && info.bus_width==64);
    assert(info.rate==2401 && info.tck_ps==833);
    assert(std::string(info.part)=="TEST-SODIMM");
    std::cout<<"Fixture: 4096 MiB, 1Rx8, 833 ps, ~2401 MT/s; two CRCs and 1024-byte read protocol OK\n";
    auto transport_case = [&](bool FakeWire::*fault, spd::Status expected) {
        FakeWire wire; wire.data=reference.data; wire.*fault=true; info.mib=999;
        assert(spd::inspect(wire,image,info)==expected && info.mib==0);
    };
    transport_case(&FakeWire::fail_select,spd::Status::page_select);
    transport_case(&FakeWire::fail_pointer,spd::Status::short_read);
    transport_case(&FakeWire::short_read,spd::Status::short_read);
    transport_case(&FakeWire::dropped_byte,spd::Status::short_read);
    transport_case(&FakeWire::ignore_page,spd::Status::page_alias);
    transport_case(&FakeWire::mutate,spd::Status::unstable);
    transport_case(&FakeWire::wrong_rpa,spd::Status::page_select);
    transport_case(&FakeWire::selector_fault,spd::Status::page_select);
    transport_case(&FakeWire::bad_stop,spd::Status::page_select);
    transport_case(&FakeWire::read_disappears,spd::Status::short_read);
    FakeWire microchip; microchip.data=reference.data; microchip.dummy_nack=true;
    assert(spd::inspect(microchip,image,info)==spd::Status::ok && microchip.dummy_reads==4);
    StuckClock pins; spd::SerialBus<StuckClock> stuck(pins);
    assert(!stuck.start() && pins.now<2100 && !stuck.stop());
    auto data_case = [&](size_t pos, uint8_t val, spd::Status expected, bool fix_crc=true) {
        auto b=reference.data; b.at(pos)=val;
        if (fix_crc) {
            uint16_t crc=spd::crc16(b.data(),126);
            b[126]=static_cast<uint8_t>(crc); b[127]=static_cast<uint8_t>(crc>>8);
        }
        info.mib=999;
        assert(spd::decode(b.data(),b.size(),info)==expected && info.mib==0);
    };
    data_case(12,0xff,spd::Status::base_crc,false);
    data_case(150,0x43,spd::Status::module_crc,false);
    data_case(2,0x12,spd::Status::type);
    data_case(3,0x83,spd::Status::type);
    data_case(1,0x21,spd::Status::revision);
    data_case(0,0xa3,spd::Status::layout);
    data_case(6,0x82,spd::Status::organization);
    data_case(12,0x41,spd::Status::organization);
    data_case(13,0x0b,spd::Status::organization);
    data_case(4,0x0f,spd::Status::organization);
    data_case(17,2,spd::Status::timing);
    data_case(18,0,spd::Status::timing);
    assert(spd::decode(reference.data.data(),256,info)==spd::Status::length && info.mib==0);
    std::cout<<"ACK/NACK selector variants, bounded stuck-clock and ten transport counterexamples, thirteen length/schema/CRC counterexamples passed.\n";
}
