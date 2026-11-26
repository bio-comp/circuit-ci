#include "../firmware/Lantern/ethernet_report.h"
#include <cassert>
#include <iostream>

ModemReport example(const char* address) {
    ModemReport r;
    r.line(address);
    r.line("+CIPETH:gateway:\"192.0.2.1\"");
    r.line("+CIPETH:netmask:\"255.255.255.0\"");
    return r;
}
int main() {
    auto good = example("+CIPETH:ip:\"192.0.2.42\"");
    assert(good.addressed());
    ModemReport bare;
    bare.line("+CIPETH:ip:198.51.100.24");
    bare.line("+CIPETH:gateway:198.51.100.1");
    bare.line("+CIPETH:netmask:255.255.255.0");
    assert(bare.addressed());
    auto unassigned = example("+CIPETH:ip:\"0.0.0.0\"");
    assert(unassigned.complete() && !unassigned.addressed());
    for (const char* line : {"OK", "+CIPETH:ip:\"1.2.3.4", "+CIPETH:ip:1.2.3.4\"", "+CIPETH:ip:\"300.1.1.1\"",
                             "+CIPETH:ip:\"1.2.3.4x\"", "+CIPETH:ip:\"1.2.3\"",
                             "+CIPETH:ip:\"2..3.4\"", "+CIPETH:bogus:\"192.0.2.4\""}) {
        assert(!example(line).complete());
    }
    good.line("+CIPETH:ip:\"192.0.2.42\"");
    assert(!good.complete());
    auto failed = example("+CIPETH:ip:\"192.0.2.42\"");
    failed.line("ERROR");
    assert(!failed.complete());
    assert(elapsed(3, UINT32_MAX - 2, 6));
    assert(!elapsed(2, UINT32_MAX - 2, 6));
    assert(pingMilliseconds("+PING:13")==13);
    assert(pingMilliseconds("+PING:0")==0);
    assert(pingMilliseconds("+PING:60000")==60000);
    for (const char* s : {"+PING:", "+PING:TIMEOUT","+PING:60001","OK","+PING:10junk","+PING:-1"}) {
        assert(pingMilliseconds(s)<0);
    }
    EchoResult echo;
    echo.begin("192.0.2.1"); echo.finish(12);
    assert(echo.valid && echo.ms==12);
    echo.begin("192.0.2.2");
    assert(!echo.valid && echo.ms==-1 && !strcmp(echo.gateway,"192.0.2.2"));
    echo.finish(-1);
    assert(echo.valid && echo.ms==-1);
    std::cout << "All IP, timing and ping controls passed\n";
}
