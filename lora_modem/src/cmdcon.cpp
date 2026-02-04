#include <logging.h>
#include <cmdcon.h>
#include <cstdint>
#include <cstring>
#include <main.h>
#include <ArduinoJson.h>
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
        JsonDocument doc;
        doc["type"] = "telemetry";
        if (!this->is_stby) {
            doc["rssi"] = radio->rssi();
        }
        serializeJson(doc, *this->stream);
        this->stream->println();
        this->prev_telem = millis();
    }
    dump_packets();
    if (this->stream->available() != 0) {
        auto jsonstr = this->stream->readStringUntil('\n');
        jsonstr.trim();
        JsonDocument doc;
        DeserializationError error = deserializeJson(doc, jsonstr);
        if (error) {
            this->stream->print("deserializeJson() failed: ");
            this->stream->println(error.f_str());
            return;
        }
        String type = doc["type"];
        if (type == "settings") {
            LOG_DEBUG("got settings");
            JsonDocument docOut;
            if (doc["gain"].is<unsigned short>()) {
                LOG_DEBUG("settings: set gain");
                unsigned short gain = doc["gain"];
                if (radio->setGain(gain)) {
                    docOut["gain"] = gain;
                }
            }

            if (doc["txPower"].is<unsigned short>()) {
                LOG_DEBUG("settings: set txPower");
                unsigned short txPower = doc["txPower"];
                if (radio->setTxPower(txPower)) {
                    docOut["txPower"] = txPower;
                }
            }

            if (doc["frequency"].is<unsigned long>()) {
                LOG_DEBUG("settings: set frequency");
                unsigned long frequency = doc["frequency"];
                if (radio->setFrequency(frequency)) {
                    docOut["frequency"] = frequency;
                }
            }

            if (doc["spreadingFactor"].is<unsigned short>()) {
                LOG_DEBUG("settings: set spreadingFactor");
                unsigned short spreadingFactor = doc["spreadingFactor"].as<unsigned short>();
                if (radio->setSpreadingFactor(spreadingFactor)) {
                    docOut["spreadingFactor"] = spreadingFactor;
                }
            }

            if (doc["signalBandwidth"].is<unsigned long>()) {
                LOG_DEBUG("settings: set signalBandwidth");
                unsigned long signalBandwidth = doc["signalBandwidth"].as<unsigned long>();
                if (radio->setSignalBandwidth(signalBandwidth)) {
                    docOut["signalBandwidth"] = signalBandwidth;
                }
            }

            if (doc["codingRate4"].is<unsigned short>()) {
                LOG_DEBUG("settings: set codingRate4");
                unsigned short codingRate4 = doc["codingRate4"].as<unsigned short>();
                if (radio->setCodingRate4(codingRate4)) {
                    docOut["codingRate4"] = codingRate4;
                }
            }

            if (doc["preambleLength"].is<unsigned short>()) {
                LOG_DEBUG("settings: set preambleLength");
                unsigned short preambleLength = doc["preambleLength"].as<unsigned short>();
                if (radio->setPreambleLength(preambleLength)) {
                    docOut["preambleLength"] = preambleLength;
                }
            }

            if (doc["syncWord"].is<uint8_t>()) {
                LOG_DEBUG("settings: set syncWord");
                uint8_t syncWord = doc["syncWord"].as<uint8_t>();
                if (radio->setSyncWord(syncWord)) {
                    docOut["syncWord"] = syncWord;
                }
            }

            if (doc["CRC"].is<bool>()) {
                LOG_DEBUG("settings: set CRC");
                bool CRC = doc["CRC"].as<bool>();
                if (radio->setCRC(CRC)) {
                    docOut["CRC"] = CRC;
                }
            }

            if (doc["invertIQ"].is<bool>()) {
                LOG_DEBUG("settings: set invertIQ");
                bool invertIQ = doc["invertIQ"].as<bool>();
                if (radio->setInvertIQ(invertIQ)) {
                    docOut["invertIQ"] = invertIQ;
                }
            }
            
            if (doc["lowDataRateOptimize"].is<bool>()) {
                LOG_DEBUG("settings: set lowDataRateOptimize");
                bool lowDataRateOptimize = doc["lowDataRateOptimize"].as<bool>();
                if (radio->setLowDataRateOptimize(lowDataRateOptimize)) {
                    docOut["lowDataRateOptimize"] = lowDataRateOptimize;
                }
            }

            if (doc["receive"].is<bool>()) {
                if (doc["receive"].as<bool>()) {
                    LOG_DEBUG("settings: set RX mode");
                    this->is_stby = false;
                    set_rx_mode();
                    docOut["receive"] = true;
                } else {
                    LOG_DEBUG("settings: set standby mode");
                    this->is_stby = true;
                    set_rx_mode();
                }
            }

            if (doc["wifi"].is<JsonObject>() && doc["wifi"]["ssid"].is<const char *>() && doc["wifi"]["password"].is<const char *>()) {
                LOG_DEBUG("settings: got wifi SSID: %s and password", doc["wifi"]["ssid"].as<const char *>());
                config_set_wifi(doc["wifi"]["ssid"], doc["wifi"]["password"]);
                config_refresh();
                docOut["wifi"]["ssid"] = doc["wifi"]["ssid"];
                docOut["wifi"]["password"] = doc["wifi"]["password"];
            }

            serializeJson(docOut, *this->stream);
            this->stream->println();
        } else if (type == "metaQ") {
            JsonDocument docOut;
            docOut["type"] = "meta";
            docOut["gainMax"] = radio->getGainMax();
            docOut["txPowerMax"] = radio->getTxPowerMax();
            serializeJson(docOut, *this->stream);
            this->stream->println();
        } else if (type == "packetTx") {
            JsonArray data = doc["data"].as<JsonArray>();
            bool cad = doc["cad"].is<bool>() && doc["cad"].as<bool>();
            unsigned long cad_wait = doc["cadWait"].is<unsigned long>() ? doc["cadWait"].as<unsigned long>() : 1;
            unsigned long cad_timeout = doc["cadTimeout"].is<unsigned long>() ? doc["cadTimeout"].as<unsigned long>() : 1;
            size_t buf_size = data.size();
            if (buf_size == 0) {
                return;
            }
            LOG_DEBUG("transmitting packet with size %zu", buf_size);
            uint8_t *buf = new uint8_t[buf_size];
            size_t buf_idx = 0;
            for (JsonVariant v : data) {
                if (!v.is<unsigned int>()) {
                    delete buf;
                    return;
                }
                buf[buf_idx++] = v.as<unsigned int>();
            }

#ifdef HAS_LED
            digitalWrite(LED_PIN, HIGH);
#endif

            const char *reason = "";
            bool tx_allowed = true;
            bool tx_success = false;

            if (cad) {
                LOG_DEBUG("waiting for channel to become inactive");
                unsigned long tstart = millis();
                while (radio->isChannelActive()) {
                    if (millis() - tstart >= cad_timeout) {
                        tx_allowed = false;
                        reason = "cadTimeout";
                        LOG_DEBUG(reason);
                    }

                    // busy. Receive and wait for cad_wait ms
                    // we don't wanna miss any packets!
                    set_rx_mode();
                    unsigned long tstart2 = millis();
                    while (millis() - tstart2 < cad_wait) {
                        delay(1);
                    }
                    yield();
                }
            }

            if (tx_allowed && radio->beginPacket()) {
                radio->write(buf, buf_size);
                if (radio->endPacket()) {
                    LOG_DEBUG("successfully transmitted packet");
                    tx_success = true;
                } else {
                    reason = "endPacket failed";
                    LOG_DEBUG(reason);
                }
            } else {
                reason = "beginPacket failed";
                LOG_DEBUG(reason);
            }

            delete buf;
            
            LOG_DEBUG("setting radio mode back");
            set_rx_mode();

            JsonDocument docOut;
            docOut["type"] = "txAck";
            docOut["id"] = doc["id"];
            docOut["success"] = tx_success;
            if (!tx_success) {
                docOut["reason"] = reason;
            }
            serializeJson(docOut, *this->stream);
            this->stream->println();
#ifdef HAS_LED
            digitalWrite(LED_PIN, LOW);
#endif
        }
    }
}

void CMDCon::dump_packets() {
    while (struct QueuePacket *p = rxQueue.readNext()) {
#ifdef HAS_LED
        digitalWrite(LED_PIN, HIGH);
#endif
        JsonDocument doc;
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
