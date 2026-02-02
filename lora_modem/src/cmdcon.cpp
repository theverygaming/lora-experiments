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

void CMDCon::set_stream(Stream *s) {
    LOG_DEBUG("set_stream");
    this->stream = s;
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
