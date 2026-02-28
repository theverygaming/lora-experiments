#pragma once
#include <LoRaRadio.h>
#include <cstdint>
#include <RadioLib.h>


class RadioSX1262 : public LoRaRadio {
public:
    RadioSX1262(SX1262 *radio);

    bool init() override;

    bool beginPacket(bool implicitHeader = false) override;
    bool endPacket(bool async = false) override;
    size_t write(const uint8_t *buf, size_t n) override;
    void onTxDone(void (*cb)()) override;
    bool isTransmitting() override;

    int packetRSSI() override;
    float packetSNR() override;
    long packetFrequencyError() override;
    void modeContinousReceive(size_t size = 0) override;
    void onReceive(void (*cb)(size_t)) override;
    bool read(void *buf, size_t len) override;

    void modeStandby() override;
    void modeSleep() override;
    bool isChannelActive() override;
    int rssi() override;

    bool setGain(unsigned short level) override;
    unsigned short getGain() override;
    unsigned short getGainMax() override;
    bool setTxPower(uint8_t dbm) override;
    uint8_t getTxPower() override;
    uint8_t getTxPowerMax() override;
    bool setFrequency(unsigned long frequencyHz) override;
    unsigned long getFrequency() override;
    bool setSpreadingFactor(unsigned short sf) override;
    unsigned short getSpreadingFactor() override;
    bool setSignalBandwidth(unsigned long sbw) override;
    unsigned long getSignalBandwidth() override;
    bool setCodingRate4(unsigned short denominator) override;
    unsigned short getCodingRate4() override;
    bool setPreambleLength(unsigned short length) override;
    unsigned short getPreambleLength() override;
    bool setSyncWord(uint8_t sw) override;
    uint8_t getSyncWord() override;
    bool setCRC(bool enabled) override;
    bool getCRC() override;
    bool setInvertIQ(bool enabled) override;
    bool getInvertIQ() override;
    bool setLowDataRateOptimize(bool enabled) override;
    bool getLowDataRateOptimize() override;

private:
    SX1262 *radio;
    uint8_t packetbuf[256];
    size_t packetbuf_idx;
    bool header_implicit;

    unsigned short _gain;
    uint8_t _txp_dbm;
    unsigned long _frequency;
    unsigned short _sf;
    unsigned long _bw;
    unsigned short _cr4;
    unsigned short _preamble_len;
    uint8_t _syncword;
    bool _crc;
    bool _invert_iq;
    bool _low_data_rate_optimize;
};
