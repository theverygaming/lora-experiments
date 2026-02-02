#pragma once
#include <LoRaRadio.h>
#include <SPI.h>

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
    unsigned short getGainMax() override;
    bool setTxPower(unsigned short dbm) override;
    unsigned short getTxPowerMax() override;
    bool setFrequency(unsigned long frequencyHz) override;
    bool setSpreadingFactor(unsigned short sf) override;
    bool setSignalBandwidth(unsigned long sbw) override;
    bool setCodingRate4(unsigned short denominator) override;
    bool setPreambleLength(unsigned short length) override;
    bool setSyncWord(uint8_t sw) override;
    bool setCRC(bool enabled) override;
    bool setInvertIQ(bool enabled) override;
    bool setLowDataRateOptimize(bool enabled) override;
};
