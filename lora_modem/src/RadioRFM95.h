#pragma once
#include <LoRaRadio.h>
#include <SPI.h>
#include <cstdint>

#ifndef RFM95_RESET
#define RFM95_RESET -1
#endif

class RadioRFM95 : public LoRaRadio {
public:
    RadioRFM95(SPIClass *spi_cls, uint32_t spi_freq, int cs, int dio0, int reset = -1);

    bool init() override;

    bool beginPacket(bool implicitHeader = false) override;
    bool endPacket(bool async = false) override;
    size_t write(const uint8_t *buf, size_t n) override;
    void onTxDone(void (*cb)()) override;
    bool isTransmitting() override;

    size_t getPacketSingle(size_t size = 0) override;
    int packetRSSI() override;
    float packetSNR() override;
    long packetFrequencyError() override;
    void modeContinousReceive(size_t size = 0) override;
    void onReceive(void (*cb)(size_t)) override;
    int read() override;

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
