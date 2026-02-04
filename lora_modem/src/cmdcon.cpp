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
        serializeJson(doc, *this->stream);*/
        this->stream->println();
        this->prev_telem = millis();
    }
    dump_packets();
    while (this->stream->available() != 0) {
        uint8_t byte = this->stream->read();

        // end of data frame
        if (in_frame && byte == FEND && active_command == )
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
        serializeJson(doc, *this->stream);*/
        this->stream->println();
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
