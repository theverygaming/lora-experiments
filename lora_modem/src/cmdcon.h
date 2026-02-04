#pragma once
#include <cstdint>
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

    // KISS frame control
    static const uint8_t FEND = 0xC0;
    static const uint8_t FESC = 0xDB;
    static const uint8_t TFEND = 0xDC;
    static const uint8_t TFESC = 0xDD;

    // KISS commands
    // https://github.com/liberatedsystems/RNode_Firmware_CE/blob/2a4d6c7a7f02a272b01c0449c728a73b9e9407af/Framing.h
    static const uint8_t CMD_UNKNOWN = 0xFE;
    static const uint8_t CMD_DATA = 0;

    // KISS state
    bool in_frame = false;
    uint8_t active_command = 0;
};

extern CMDCon CMDConGlobal;
