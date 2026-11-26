#pragma once
#include <stdint.h>
#include <string.h>
#include <stdio.h>

// A successful query establishes only what the modem reports about its own IPv4 configuration.
struct ModemReport {
    char ip[16]{};
    char gateway[16]{};
    char mask[16]{};
    unsigned seen = 0;
    bool invalid = false;

    static bool ipv4(const char* p) {
        for (int octet = 0; octet < 4; ++octet) {
            unsigned value = 0;
            int digits = 0;
            while (*p >= '0' && *p <= '9') {
                value = value * 10 + unsigned(*p++ - '0');
                if (++digits > 3 || value > 255) return false;
            }
            if (!digits || (octet < 3 && *p++ != '.')) return false;
        }
        return *p == 0;
    }

    void field(const char* value, char* dest, unsigned bit) {
        size_t n = strlen(value);
        if (n>=2 && value[0]=='"' && value[n-1]=='"') {
            ++value;
            n-=2;
        }
        if ((seen & bit) || !n || n>15) {
            invalid=true;
            return;
        }
        memcpy(dest,value,n);
        dest[n]=0;
        if (!ipv4(dest)) invalid = true;
        seen |= bit;
    }

    void line(const char* s) {
        if (strncmp(s,"+CIPETH:ip:",11)==0) field(s+11,ip,1);
        else if (strncmp(s,"+CIPETH:gateway:",16)==0) field(s+16,gateway,2);
        else if (strncmp(s,"+CIPETH:netmask:",16)==0) field(s+16,mask,4);
        else if (strncmp(s,"+CIPETH:",8)==0 || strcmp(s,"ERROR")==0) invalid=true;
    }
    bool complete() const { return !invalid && seen == 7; }
    bool addressed() const { return complete() && strcmp(ip, "0.0.0.0") != 0; }
};

inline bool elapsed(uint32_t now, uint32_t then, uint32_t interval) {
    return uint32_t(now - then) >= interval;
}

// Return -1 on malformed timing or timeout. Require the final OK separately.
inline int pingMilliseconds(const char* line) {
    if (strncmp(line,"+PING:",6)!=0) return -1;
    const char* p=line+6;
    if (!*p) return -1;
    int ms=0;
    for (;*p;++p) {
        if (*p<'0' || *p>'9' || ms>6000) return -1;
        ms=ms*10+*p-'0';
    }
    return ms<=60000 ? ms : -1;
}

struct EchoResult {
    char gateway[16]{};
    int ms=-1;
    bool valid=false;
    void begin(const char* address) {
        valid=false;
        ms=-1;
        snprintf(gateway,sizeof gateway,"%s",address);
    }
    void finish(int completedMs) { ms=completedMs; valid=true; }
};
