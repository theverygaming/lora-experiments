#include <RadioRFM95.h>
#include <LoRa.h>
#include <cstdint>
#include <logging.h>

RadioRFM95::RadioRFM95(SPIClass *spi_cls, uint32_t spi_freq, int cs, int dio0, int reset) {
    LoRa.setPins(cs, reset, dio0);
    LoRa.setSPI(*spi_cls);
    LoRa.setSPIFrequency(spi_freq);
    LOG_DEBUG("RadioRFM95 constructed with spi_cls: %p spi_freq: %lu cs: %d dio0: %d reset: %d", spi_cls, (unsigned long)spi_freq, cs, dio0, reset);
}

bool RadioRFM95::init() {
    int res = LoRa.begin(868E6);
    LOG_DEBUG("RadioRFM95: LoRa.begin -> %d", res);
    return res != 0;
}

bool RadioRFM95::beginPacket(bool implicitHeader) {
    return LoRa.beginPacket(implicitHeader);
}

bool RadioRFM95::endPacket(bool async) {
    return LoRa.endPacket(async);
}

size_t RadioRFM95::write(const uint8_t *buf, size_t n) {
    return LoRa.write(buf, n);
}

void RadioRFM95::onTxDone(void (*cb)()) {
    LoRa.onTxDone(cb);
}

extern "C" bool _ZN9LoRaClass14isTransmittingEv(LoRaClass *);

bool RadioRFM95::isTransmitting() {
    // it is 6:41 in the morning and the silly has gotten to me
    // this method is private but I wanted to call it. So I will!
    // NOBODY CAN STOP ME :3
    return _ZN9LoRaClass14isTransmittingEv(&LoRa);
}

int RadioRFM95::packetRSSI() {
    return LoRa.packetRssi();
}

float RadioRFM95::packetSNR() {
    return LoRa.packetSnr();
}

long RadioRFM95::packetFrequencyError() {
    // the library function is seemingly unreliable, crashes in some cases (continous RX mode)... So we won't use it
    return 0;
}

void RadioRFM95::modeContinousReceive(size_t size) {
    LoRa.receive(size);
}

void RadioRFM95::onReceive(void (*cb)(size_t)) {
    static void (*cb_global)(size_t) = nullptr;

    cb_global = cb;
    auto cb_translated = [](int n) {
        if (cb_global != nullptr) {
            cb_global(n);
        }
    };
    if (cb != nullptr) {
        LoRa.onReceive(cb_translated);
    } else {
        LoRa.onReceive(nullptr);
    }
}

bool RadioRFM95::read(void *buf_, size_t len) {
    uint8_t *buf = (uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        int r = LoRa.read();
        if (r < 0) {
            return false;
        }
        buf[i] = r;
    }
    return true;
}

void RadioRFM95::modeStandby() {
    LoRa.idle();
}

void RadioRFM95::modeSleep() {
    LoRa.sleep();
}

bool RadioRFM95::isChannelActive() {
    static volatile bool cad_done;
    static bool cad_detected;
    cad_done = false;
    modeStandby();
    LoRa.onCadDone([](bool active){
        cad_detected = active;
        cad_done = true;
    });
    unsigned long tstart = millis();
    LoRa.channelActivityDetection();
    while (!cad_done) {
        // hard timeout after 10s
        if (millis() - tstart > 1000*10) {
            LOG_DEBUG("CAD 10s timeout");
            cad_done = true;
            cad_detected = true; // if CAD doesn't work we are always busy
            // since we didn't get any interrupt chip is probably still trying to CAD
            // so we stop CAD by going into standby
            modeStandby();
        }
        yield();
    }
    return cad_detected;
}

int RadioRFM95::rssi() {
    return LoRa.rssi();
}

bool RadioRFM95::setGain(unsigned short level) {
    if (level > 6) {
        level = 6;
    }
    LoRa.setGain(level);
    this->_gain = level;
    return true;
}

unsigned short RadioRFM95::getGain() {
    return this->_gain;
}

unsigned short RadioRFM95::getGainMax() {
    return 6;
}

bool RadioRFM95::setTxPower(uint8_t dbm) {
    if (dbm > 20) {
        dbm = 20;
    }
    LoRa.setTxPower(dbm);
    this->_txp_dbm = dbm;
    return true;
}

uint8_t RadioRFM95::getTxPower() {
    return this->_txp_dbm;
}

uint8_t RadioRFM95::getTxPowerMax() {
    return 20;
}

bool RadioRFM95::setFrequency(unsigned long frequencyHz) {
    LoRa.setFrequency(frequencyHz);
    this->_frequency = frequencyHz;
    return true;
}

unsigned long RadioRFM95::getFrequency() {
    return this->_frequency;
}

bool RadioRFM95::setSpreadingFactor(unsigned short sf) {
    if (sf > 12) {
        sf = 12;
    } else if (sf < 6) {
        sf = 6;
    }
    LoRa.setSpreadingFactor(sf);
    this->_sf = sf;
    return true;
}

unsigned short RadioRFM95::getSpreadingFactor() {
    return this->_sf;
}

bool RadioRFM95::setSignalBandwidth(unsigned long sbw) {
    if (sbw > 500000) {
        sbw = 500000;
    } else if (sbw < 7800) {
        sbw = 7800;
    }
    LoRa.setSignalBandwidth(sbw);
    this->_bw = sbw;
    return true;
}

unsigned long RadioRFM95::getSignalBandwidth() {
    return this->_bw;
}

bool RadioRFM95::setCodingRate4(unsigned short denominator) {
    if (denominator > 8) {
        denominator = 8;
    } else if (denominator < 5) {
        denominator = 5;
    }
    LoRa.setCodingRate4(denominator);
    this->_cr4 = denominator;
    return true;
}

unsigned short RadioRFM95::getCodingRate4() {
    return this->_cr4;
}

bool RadioRFM95::setPreambleLength(unsigned short length) {
    LoRa.setPreambleLength(length);
    this->_preamble_len = length;
    return true;
}

unsigned short RadioRFM95::getPreambleLength() {
    return this->_preamble_len;
}

bool RadioRFM95::setSyncWord(uint8_t sw) {
    LoRa.setSyncWord(sw);
    this->_syncword = sw;
    return true;
}

uint8_t RadioRFM95::getSyncWord() {
    return this->_syncword;
}

bool RadioRFM95::setCRC(bool enabled) {
    if(enabled) {
        LoRa.enableCrc();
    } else {
        LoRa.disableCrc();
    }
    this->_crc = enabled;
    return true;
}

bool RadioRFM95::getCRC() {
    return this->_crc;
}

bool RadioRFM95::setInvertIQ(bool enabled) {
    if(enabled) {
        LoRa.enableInvertIQ();
    } else {
        LoRa.disableInvertIQ();
    }
    this->_invert_iq = enabled;
    return true;
}

bool RadioRFM95::getInvertIQ() {
    return this->_invert_iq;
}

bool RadioRFM95::setLowDataRateOptimize(bool enabled) {
    if(enabled) {
        LoRa.enableLowDataRateOptimize();
    } else {
        LoRa.disableLowDataRateOptimize();
    }
    this->_low_data_rate_optimize = enabled;
    return true;
}

bool RadioRFM95::getLowDataRateOptimize() {
    return this->_low_data_rate_optimize;
}
