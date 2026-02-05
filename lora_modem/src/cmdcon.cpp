#include <logging.h>
#include <cmdcon.h>
#include <cstdint>
#include <cstring>
#include <main.h>
#include <variant.h>
#include <config.h>

CMDCon CMDConGlobal;

void CMDCon::rx_hook(size_t psize) {
    if (psize > MAX_PACKET_LEN) {
        return; // drop that packet
    }
    struct QueuePacket *p = CMDConGlobal.rxQueue.writeNext();
    if (p == nullptr) {
        return;
    }
    p->rssi = radio->packetRSSI();
    p->snr = radio->packetSNR();
    p->freqError = radio->packetFrequencyError();
    p->plen = psize;
    for (size_t i = 0; i < psize; i++) {
        p->data[i] = radio->read();
    }
}

class DummyStream : public Stream {
public:
    DummyStream() {}
    int available() override { return 0; }
    int read() override { return -1; }
    int peek() override { return -1; }
    void flush() override {}
    size_t write(uint8_t) override { return 1; }
    size_t write(const uint8_t* buf, size_t size) override { return size; }
} dummyStream;

void CMDCon::set_stream(Stream *s, void (*unset_cb)()) {
    if (this->stream == s) {
        return;
    }
    LOG_DEBUG("set_stream %p, unset_cb %p", s, unset_cb);
    if (this->stream_unset_cb != nullptr) {
        LOG_DEBUG("calling stream_unset_cb");
        this->stream_unset_cb();
        this->stream_unset_cb = nullptr;
    }
    if (s != nullptr) {
        this->stream = s;
    } else {
        // Setting the stream to nullptr from interrupt context while running can result in crashes
        // this is because the function that uses the stream may have been interrupted and is far past it's stream == nullptr check!
        // So we set it to a dummy stream instead tehee
        this->stream = &dummyStream;
    }
    this->stream_unset_cb = unset_cb;
    radio->onReceive(rx_hook);
    radio->modeStandby();
    this->is_stby = true;
}

void CMDCon::process() {
    if (this->stream == nullptr) {
        return;
    }
    if (millis() - this->prev_telem > 2 * 1000) {
        /*JsonDocument doc;
        doc["type"] = "telemetry";
        if (!this->is_stby) {
            doc["rssi"] = radio->rssi();
        }
        serializeJson(doc, *this->stream);
        this->stream->println();*/
        this->prev_telem = millis();
    }
    dump_packets();
    while (this->stream->available() != 0) {
        static uint8_t kiss_buf[MAX_KISS_CMD_LEN];
        uint8_t byte = this->stream->read();

        if (in_frame && byte == FEND && active_cmd == CMD_DATA) { // end of data frame
            in_frame = false;
            // TODO: finish data frame, queue packet for tx
            continue;
        } else if (byte == FEND) { // start of command
            in_frame = true;
            active_cmd = CMD_UNKNOWN;
            frame_len = 0;
            escape_active = false;
            continue;
        } else if (in_frame && frame_len == 0 && active_cmd == CMD_UNKNOWN) { // command byte
            active_cmd = byte;
            continue;
        }

        // not in frame at this point? abort
        if (!in_frame) {
            continue;
        }

        // handle escape
        if (byte != FESC) {
            if (escape_active) {
                if (byte == TFEND) {
                    byte = FEND;
                } else if (byte == TFESC) {
                    byte = FESC;
                }
                escape_active = false;
            }
        } else {
            escape_active = true;
            continue;
        }

        // fill buffer
        if (frame_len < MAX_KISS_CMD_LEN) {
            kiss_buf[frame_len++] = byte;
        } else { // no more buffer space, skip
            continue;
        }

        // normal command processing
        switch (active_cmd) {
            case CMD_DATA: {
                // FIXME: append command buffer
                break;
            }
            case CMD_FREQUENCY: {
                if (frame_len == 4) {
                    // !! endianness
                    unsigned long freq = *((uint32_t *)kiss_buf);
                    if (freq != 0) { // freq = 0 is for reading
                        radio->setFrequency(freq);
                    }
                    // !! endianness
                    uint32_t freq_read = radio->getFrequency();
                    kiss_cmd_resp(CMD_FREQUENCY, &freq_read, sizeof(freq_read));
                }
                break;
            }
            case CMD_BANDWIDTH: {
                if (frame_len == 4) {
                    // !! endianness
                    unsigned long bw = *((uint32_t *)kiss_buf);
                    if (bw != 0) { // bw = 0 is for reading
                        radio->setSignalBandwidth(bw);
                    }
                    // !! endianness
                    uint32_t bw_read = radio->getSignalBandwidth();
                    kiss_cmd_resp(CMD_BANDWIDTH, &bw_read, sizeof(bw_read));
                }
                break;
            }
            case CMD_TXPOWER: {
                if (frame_len == 1) {
                    uint8_t txp = kiss_buf[0];
                    if (txp != 0xFF) { // txp = 0xFF is for reading
                        radio->setTxPower(txp);
                    }
                    uint8_t txp_read = radio->getTxPower();
                    kiss_cmd_resp(CMD_TXPOWER, &txp_read, sizeof(txp_read));
                }
                break;
            }
            case CMD_SF: {
                if (frame_len == 1) {
                    uint8_t sf = kiss_buf[0];
                    if (sf != 0xFF) { // sf = 0xFF is for reading
                        radio->setSpreadingFactor(sf);
                    }
                    uint8_t sf_read = radio->getSpreadingFactor();
                    kiss_cmd_resp(CMD_SF, &sf_read, sizeof(sf_read));
                }
                break;
            }
            case CMD_CR: {
                if (frame_len == 1) {
                    uint8_t cr4 = kiss_buf[0];
                    if (cr4 != 0xFF) { // cr4 = 0xFF is for reading
                        radio->setCodingRate4(cr4);
                    }
                    uint8_t cr4_read = radio->getCodingRate4();
                    kiss_cmd_resp(CMD_CR, &cr4_read, sizeof(cr4_read));
                }
                break;
            }
            // TODO: CMD_IMPLICIT
            // TODO: CMD_LEAVE
            // TODO: CMD_RADIO_STATE
            // TODO: CMD_ST_ALOCK
            // TODO: CMD_LT_ALOCK
            // TODO: CMD_STAT_RX
            // TODO: CMD_STAT_TX
            // TODO: CMD_STAT_RSSI
            // TODO: CMD_RADIO_LOCK
            // TODO: CMD_BLINK
            // TODO: CMD_RANDOM
            case CMD_DETECT: {
                if (frame_len == 1 && kiss_buf[0] == DETECT_REQ) {
                    const uint8_t detect_resp = DETECT_RESP;
                    kiss_cmd_resp(CMD_DETECT, &detect_resp, sizeof(detect_resp));
                }
                break;
            }
            // TODO: CMD_PROMISC
            // TODO: CMD_READY
            // TODO: CMD_UNLOCK_ROM
            // TODO: CMD_RESET
            // TODO: CMD_ROM_READ
            // TODO: CMD_CFG_READ
            // TODO: CMD_ROM_WRITE
            case CMD_FW_VERSION: {
                const uint8_t fw_vers[2] = {0x01, 0x55}; // RNode version on gh at 2026-02-05
                kiss_cmd_resp(CMD_FW_VERSION, &fw_vers, sizeof(fw_vers));
                break;
            }
            // TODO: CMD_PLATFORM
            // TODO: CMD_MCU
            // TODO: CMD_BOARD
            // TODO: CMD_CONF_SAVE
            // TODO: CMD_CONF_DELETE
            // TODO: CMD_FB_EXT
            // TODO: CMD_FB_WRITE
            // TODO: CMD_FB_READ
            // TODO: CMD_DISP_READ
            // TODO: CMD_DEV_HASH
            // TODO: CMD_DEV_SIG
            // TODO: CMD_FW_UPD
            // TODO: CMD_HASHES
            // TODO: CMD_FW_HASH
            // TODO: CMD_WIFI_CHN
            // TODO: CMD_WIFI_MODE
            // TODO: CMD_WIFI_SSID
            // TODO: CMD_WIFI_PSK
            // TODO: CMD_WIFI_IP
            // TODO: CMD_WIFI_NM
            // TODO: CMD_BT_CTRL
            // TODO: CMD_BT_UNPAIR
            // TODO: CMD_DISP_INT
            // TODO: CMD_DISP_ADDR
            // TODO: CMD_DISP_BLNK
            // TODO: CMD_DISP_ROT
            // TODO: CMD_DIS_IA
            // TODO: CMD_DISP_RCND
            // TODO: CMD_NP_INT
        }
    }
}

void CMDCon::dump_packets() {
    while (struct QueuePacket *p = rxQueue.readNext()) {
#ifdef HAS_LED
        digitalWrite(LED_PIN, HIGH);
#endif
        /*JsonDocument doc;
        doc["type"] = "packetRx";
        doc["rssi"] = p->rssi;
        doc["snr"] = p->snr;
        doc["freqError"] = p->freqError;
        JsonArray arr = doc["data"].to<JsonArray>();
        // FIXME: improve perf
        for (size_t i = 0; i < p->plen; i++) {
            arr.add(p->data[i]);
        }
        serializeJson(doc, *this->stream);
        this->stream->println();*/
        rxQueue.readNextDone();
    }
#ifdef HAS_LED
    digitalWrite(LED_PIN, LOW);
#endif
}

void CMDCon::set_rx_mode() {
    if (!this->is_stby) {
        radio->modeContinousReceive();
    } else {
        radio->modeStandby();
    }
}


void CMDCon::kiss_escaped_write(const void *buf, size_t size) {
    uint8_t *buf_u8 = (uint8_t *)buf;
    for (size_t i = 0; i < size; i++) {
        uint8_t b = buf_u8[i];
        if (b == FEND) {
            this->stream->write(FESC);
            b = TFEND;
        } else if (b == FESC) {
            this->stream->write(FESC);
            b = TFESC;
        }
        this->stream->write(b);
    }
}

void CMDCon::kiss_cmd_resp(uint8_t cmd, const void *buf, size_t size) {
    this->stream->write(FEND);
    this->stream->write(cmd);
    kiss_escaped_write(buf, size);
    this->stream->write(FEND);
    this->stream->flush();
}
