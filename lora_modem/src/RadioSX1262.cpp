#include <RadioSX1262.h>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <logging.h>


RadioSX1262::RadioSX1262(SX1262 *_radio) {
    this->radio = _radio;
}

bool RadioSX1262::init() {
    int16_t status = this->radio->begin();
    if (status == RADIOLIB_ERR_NONE) {
        return true;
    }
    LOG_ERROR("failed to init radio, code: %d", status);
    return false;
}

bool RadioSX1262::beginPacket(bool implicitHeader) {
    this->packetbuf_idx = 0;
    this->header_implicit = implicitHeader;
    return true;
}

bool RadioSX1262::endPacket(bool async) {
    if (async) {
        return false;
    }
    if (this->header_implicit) {
        this->radio->implicitHeader(this->packetbuf_idx);
    } else {
        this->radio->explicitHeader();
    }
    int16_t status = this->radio->transmit(this->packetbuf, this->packetbuf_idx);
    if (status == RADIOLIB_ERR_NONE) {
        return true;
    }
    LOG_ERROR("error transmitting, code: %d", status);
    return false;
}

size_t RadioSX1262::write(const uint8_t *buf, size_t n) {
    size_t buf_avl = sizeof(this->packetbuf) - this->packetbuf_idx;
    if (n > buf_avl) {
        n = buf_avl;
    }

    if (n) {
        memcpy(this->packetbuf, buf, n);
        this->packetbuf_idx += n;
    }

    return n;
}

void RadioSX1262::onTxDone(void (*cb)()) {
    // FIXME:
}

bool RadioSX1262::isTransmitting() {
    //FIXME:
    return false;
}

int RadioSX1262::packetRSSI() {
    return this->radio->getRSSI(true);
}

float RadioSX1262::packetSNR() {
    return this->radio->getSNR();
}

long RadioSX1262::packetFrequencyError() {
    // only to be used with caution for SX126x (undocumented), so for the sake of stability let's not use it
    return 0;
}

void RadioSX1262::modeContinousReceive(size_t size) {
    if (size == 0) {
        this->radio->explicitHeader();
    } else {
        this->radio->implicitHeader(size);  
    }
    int16_t status = this->radio->startReceive();
    if (status == RADIOLIB_ERR_NONE) {
        return;
    }
    LOG_ERROR("error starting rx, code: %d", status);
}

void RadioSX1262::onReceive(void (*cb)(size_t)) {
    static void (*cb_global)(size_t) = nullptr;
    static RadioSX1262 *sx1262_global = nullptr;

    sx1262_global = this;
    cb_global = cb;
    auto cb_translated = []() {
        size_t len = sx1262_global->radio->getPacketLength();
        if (cb_global != nullptr) {
            cb_global(len);
        }
    };
    if (cb != nullptr) {
        this->radio->setPacketReceivedAction(cb_translated);
    } else {
        this->radio->clearPacketReceivedAction();
    }
}

bool RadioSX1262::read(void *buf, size_t len) {
    int16_t status = this->radio->readData((uint8_t *)buf, len);
    if (status == RADIOLIB_ERR_NONE) {
        return true;
    }
    LOG_ERROR("error reading data, code: %d", status);
    return false;
}

void RadioSX1262::modeStandby() {
    this->radio->finishReceive();
}

void RadioSX1262::modeSleep() {
    // FIXME:
}

bool RadioSX1262::isChannelActive() {
    // FIXME:
    return false;
}

int RadioSX1262::rssi() {
    return this->radio->getRSSI(false);
}

bool RadioSX1262::setGain(unsigned short level) {
    if (level > 6) {
        level = 6;
    }
    // FIXME:
    int16_t status = this->radio->setRxBoostedGainMode(true);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting gain, code: %d", status);
        return false;
    }
    this->_gain = level;
    return true;
}

unsigned short RadioSX1262::getGain() {
    return this->_gain;
}

unsigned short RadioSX1262::getGainMax() {
    return 6;
}

bool RadioSX1262::setTxPower(uint8_t dbm) {
    if (dbm > 22) {
        dbm = 22;
    }
    int16_t status = this->radio->setOutputPower(dbm);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting output power, code: %d", status);
        return false;
    }
    this->_txp_dbm = dbm;
    return true;
}

uint8_t RadioSX1262::getTxPower() {
    return this->_txp_dbm;
}

uint8_t RadioSX1262::getTxPowerMax() {
    return 22;
}

bool RadioSX1262::setFrequency(unsigned long frequencyHz) {
    int16_t status = this->radio->setFrequency((float)frequencyHz / 1000000.0f);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting frequency, code: %d", status);
        return false;
    }
    this->_frequency = frequencyHz;
    return true;
}

unsigned long RadioSX1262::getFrequency() {
    return this->_frequency;
}

bool RadioSX1262::setSpreadingFactor(unsigned short sf) {
    if (sf > 12) {
        sf = 12;
    } else if (sf < 5) {
        sf = 5;
    }
    int16_t status = this->radio->setSpreadingFactor(sf);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting spreading factor, code: %d", status);
        return false;
    }
    this->_sf = sf;
    return true;
}

unsigned short RadioSX1262::getSpreadingFactor() {
    return this->_sf;
}

bool RadioSX1262::setSignalBandwidth(unsigned long sbw) {
    if (sbw > 500000) {
        sbw = 500000;
    } else if (sbw < 7800) {
        sbw = 7800;
    }
    int16_t status = this->radio->setBandwidth(sbw / 1000.0f);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting bandwidth, code: %d", status);
        return false;
    }
    this->_bw = sbw;
    return true;
}

unsigned long RadioSX1262::getSignalBandwidth() {
    return this->_bw;
}

bool RadioSX1262::setCodingRate4(unsigned short denominator) {
    if (denominator > 8) {
        denominator = 8;
    } else if (denominator < 5) {
        denominator = 5;
    }
    int16_t status = this->radio->setCodingRate(denominator);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting coding rate, code: %d", status);
        return false;
    }
    this->_cr4 = denominator;
    return true;
}

unsigned short RadioSX1262::getCodingRate4() {
    return this->_cr4;
}

bool RadioSX1262::setPreambleLength(unsigned short length) {
    int16_t status = this->radio->setPreambleLength(length);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting preamble length, code: %d", status);
        return false;
    }
    this->_preamble_len = length;
    return true;
}

unsigned short RadioSX1262::getPreambleLength() {
    return this->_preamble_len;
}

bool RadioSX1262::setSyncWord(uint8_t sw) {
    int16_t status = this->radio->setSyncWord(sw);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting syncword, code: %d", status);
        return false;
    }
    this->_syncword = sw;
    return true;
}

uint8_t RadioSX1262::getSyncWord() {
    return this->_syncword;
}

bool RadioSX1262::setCRC(bool enabled) {
    // TODO: we got CRC len here.. should that be configurable by the user?
    int16_t status = this->radio->setCRC(enabled ? 1 : 0);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting CRC, code: %d", status);
        return false;
    }
    this->_crc = enabled;
    return true;
}

bool RadioSX1262::getCRC() {
    return this->_crc;
}

bool RadioSX1262::setInvertIQ(bool enabled) {
    int16_t status = this->radio->invertIQ(enabled);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting invert IQ, code: %d", status);
        return false;
    }
    this->_invert_iq = enabled;
    return true;
}

bool RadioSX1262::getInvertIQ() {
    return this->_invert_iq;
}

bool RadioSX1262::setLowDataRateOptimize(bool enabled) {
    int16_t status = this->radio->forceLDRO(enabled);
    if (status != RADIOLIB_ERR_NONE) {
        LOG_ERROR("error setting invert IQ, code: %d", status);
        return false;
    }
    this->_low_data_rate_optimize = enabled;
    return true;
}

bool RadioSX1262::getLowDataRateOptimize() {
    return this->_low_data_rate_optimize;
}
