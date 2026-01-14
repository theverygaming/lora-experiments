#include <logging.h>
#include <cmdcon.h>
#include <cstdint>
#include <cstring>
#include <main.h>
#include <ArduinoJson.h>
#include <variant.h>

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
    radio->modeContinousReceive();
    this->is_stby = true;
}

void CMDCon::process() {
    if (this->stream == nullptr) {
        return;
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

            if (doc["receive"].as<bool>()) {
                LOG_DEBUG("settings: set RX mode");
                radio->modeContinousReceive();
                this->is_stby = false;
                docOut["receive"] = true;
            } else {
                LOG_DEBUG("settings: set standby mode");
                radio->modeStandby();
                this->is_stby = true;
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
            
            LOG_DEBUG("waiting for channel to become inactive");
            long tstart = millis();
            while (radio->isChannelActive()) {
                if ((millis() - tstart) > 1000*10) {
                    tx_allowed = false;
                    reason = "timeout (10s) waiting for channel to clear";
                    LOG_DEBUG(reason);
                    break;
                }
                delay(10);
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
            if (!this->is_stby) {
                radio->modeContinousReceive();
            } else {
                radio->modeStandby();
            }

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
