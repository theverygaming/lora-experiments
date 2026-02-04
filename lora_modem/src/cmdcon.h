#pragma once
#include <stdint.h>
#include <stddef.h>
#include <Arduino.h>
#include <Queue.h>

class CMDCon {
public:
    void set_stream(Stream *s, void (*unset_cb)());
    void process();
private:
    static const size_t MAX_PACKET_LEN = 256;
    static const size_t RX_QUEUE_SIZE = 20;

    struct QueuePacket {
        int rssi;
        float snr;
        long freqError;
        size_t plen;
        uint8_t data[MAX_PACKET_LEN];
    };

    Queue<struct QueuePacket, 10> rxQueue;

    Stream *stream = nullptr;
    void (*stream_unset_cb)() = nullptr;
    void dump_packets();
    bool is_stby = true;
    static void rx_hook(size_t psize);
    void set_rx_mode();
    unsigned long prev_telem = 0;
};

extern CMDCon CMDConGlobal;
