#pragma once
#include <cstdint>
#include <stdint.h>
#include <stddef.h>

class LoRaRadio {
public:
    // returns true on success
    virtual bool init() = 0;

    //// TX

    virtual bool beginPacket(bool implicitHeader = false) = 0;
    virtual bool endPacket(bool async = false) = 0;
    virtual size_t write(const uint8_t *buf, size_t n) = 0;
    // called whenever a transmission finishes NOTE: this gets called from interrupt context!
    virtual void onTxDone(void (*cb)()) = 0;
    // if the radio is currently transmitting
    virtual bool isTransmitting() = 0;

    //// RX

    // RSSI of packet in dBm
    virtual int packetRSSI() = 0;
    // SNR of packet in dB
    virtual float packetSNR() = 0;
    // frequency error of packet in Hz
    virtual long packetFrequencyError() = 0;
    // continuous receive mode, used together with onReceive, nonzero size means implicit header mode
    virtual void modeContinousReceive(size_t size = 0) = 0;
    // onReceive callback, used in continuous receive mode - NOTE: this gets called from interrupt context!
    virtual void onReceive(void (*cb)(size_t)) = 0;
    // read a byte from the modem (returns false on failure)
    virtual bool read(void *buf, size_t len) = 0;

    //// OTHER

    // Standby mode
    virtual void modeStandby() = 0;
    // Sleep mode
    virtual void modeSleep() = 0;
    // check if the channel is actively in use, NOTE: puts the radio into Standby mode afterwards
    virtual bool isChannelActive() = 0;
    // current reported RSSI by the LoRa module, can be read at any time
    virtual int rssi() = 0;

    //// LoRa settings - most of the set functions return a boolean, if true the change was successful

    // LNA gain (0=AGC, then levels up to getGainMax())
    virtual bool setGain(unsigned short level) = 0;
    virtual unsigned short getGain() = 0;
    // returns maximum gain value
    virtual unsigned short getGainMax() = 0;
    // set TX power in dBm
    virtual bool setTxPower(uint8_t dbm) = 0;
    virtual uint8_t getTxPower() = 0;
    // returns the maximum possible TX power in dBm
    virtual uint8_t getTxPowerMax() = 0;
    // set the frequency in Hz
    virtual bool setFrequency(unsigned long frequencyHz) = 0;
    virtual unsigned long getFrequency() = 0;
    // set the LoRa Spreading Factor
    virtual bool setSpreadingFactor(unsigned short sf) = 0;
    virtual unsigned short getSpreadingFactor() = 0;
    // set the bandwidth in Hz
    virtual bool setSignalBandwidth(unsigned long sbw) = 0;
    virtual unsigned long getSignalBandwidth() = 0;
    // set the Coding Rate (4/denominator)
    virtual bool setCodingRate4(unsigned short denominator) = 0;
    virtual unsigned short getCodingRate4() = 0;
    // sets the preamble length in bits
    virtual bool setPreambleLength(unsigned short length) = 0;
    virtual unsigned short getPreambleLength() = 0;
    // sets the sync word
    virtual bool setSyncWord(uint8_t sw) = 0;
    virtual uint8_t getSyncWord() = 0;
    // set the CRC mode
    virtual bool setCRC(bool enabled) = 0;
    virtual bool getCRC() = 0;
    // set the IQ inversion mode
    virtual bool setInvertIQ(bool enabled) = 0;
    virtual bool getInvertIQ() = 0;
    // set the Low Data Rate Optimization mode
    virtual bool setLowDataRateOptimize(bool enabled) = 0;
    virtual bool getLowDataRateOptimize() = 0;
};
