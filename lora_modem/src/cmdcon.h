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

    static const size_t MAX_KISS_CMD_LEN = 300;

    // KISS frame control
    static const uint8_t FEND = 0xC0;
    static const uint8_t FESC = 0xDB;
    static const uint8_t TFEND = 0xDC;
    static const uint8_t TFESC = 0xDD;

    // KISS commands
    // https://github.com/liberatedsystems/RNode_Firmware_CE/blob/2a4d6c7a7f02a272b01c0449c728a73b9e9407af/Framing.h
    static const uint8_t CMD_UNKNOWN = 0xFE;
    static const uint8_t CMD_DATA = 0x00;
    static const uint8_t CMD_FREQUENCY = 0x01;
    static const uint8_t CMD_BANDWIDTH = 0x02;
    static const uint8_t CMD_TXPOWER = 0x03;
    static const uint8_t CMD_SF = 0x04;
    static const uint8_t CMD_CR = 0x05;
    // [...]
    static const uint8_t CMD_DETECT = 0x08;

    static const uint8_t DETECT_REQ = 0x73;
    static const uint8_t DETECT_RESP = 0x46;

    static const uint8_t CMD_FW_VERSION = 0x50;

    // KISS state
    bool in_frame = false;
    uint8_t active_cmd = 0;
    bool escape_active = false;
    size_t frame_len = 0;

    void kiss_escaped_write(const void *buf, size_t size);
    void kiss_cmd_resp(uint8_t cmd, const void *buf, size_t size);
};

extern CMDCon CMDConGlobal;
