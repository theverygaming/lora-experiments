#pragma once
#include <cstdint>
#include <stdint.h>
#include <stddef.h>

class LoRaRadio {
public:
    // returns true on success
    virtual bool init();

    //// TX

    virtual bool beginPacket(bool implicitHeader = false);
    virtual bool endPacket(bool async = false);
    virtual size_t write(const uint8_t *buf, size_t n);
    // called whenever a transmission finishes NOTE: this gets called from interrupt context!
    virtual void onTxDone(void (*cb)());
    // if the radio is currently transmitting
    virtual bool isTransmitting();

    //// RX

    // gets the next packet if available (single receive mode!), nonzero size means implicit header mode
    virtual size_t getPacketSingle(size_t size = 0);
    // RSSI of packet in dBm
    virtual int packetRSSI();
    // SNR of packet in dB
    virtual float packetSNR();
    // frequency error of packet in Hz
    virtual long packetFrequencyError();
    // continuous receive mode, used together with onReceive, nonzero size means implicit header mode
    virtual void modeContinousReceive(size_t size = 0);
    // onReceive callback, used in continuous receive mode - if set will make getPacketSingle not return as usual and fire instead NOTE: this gets called from interrupt context!
    virtual void onReceive(void (*cb)(size_t));
    // read a byte from the modem (returns -1 on failure)
    virtual int read();

    //// OTHER

    // Standby mode
    virtual void modeStandby();
    // Sleep mode
    virtual void modeSleep();
    // check if the channel is actively in use, NOTE: puts the radio into Standby mode afterwards
    virtual bool isChannelActive();
    // current reported RSSI by the LoRa module, can be read at any time
    virtual int rssi();

    //// LoRa settings - most of the set functions return a boolean, if true the change was successful

    // LNA gain (0=AGC, then levels up to getGainMax())
    virtual bool setGain(unsigned short level);
    virtual unsigned short getGain();
    // returns maximum gain value
    virtual unsigned short getGainMax();
    // set TX power in dBm
    virtual bool setTxPower(uint8_t dbm);
    virtual uint8_t getTxPower();
    // returns the maximum possible TX power in dBm
    virtual uint8_t getTxPowerMax();
    // set the frequency in Hz
    virtual bool setFrequency(unsigned long frequencyHz);
    virtual unsigned long getFrequency();
    // set the LoRa Spreading Factor
    virtual bool setSpreadingFactor(unsigned short sf);
    virtual unsigned short getSpreadingFactor();
    // set the bandwidth in Hz
    virtual bool setSignalBandwidth(unsigned long sbw);
    virtual unsigned long getSignalBandwidth();
    // set the Coding Rate (4/denominator)
    virtual bool setCodingRate4(unsigned short denominator);
    virtual unsigned short getCodingRate4();
    // sets the preamble length in bits
    virtual bool setPreambleLength(unsigned short length);
    virtual unsigned short getPreambleLength();
    // sets the sync word
    virtual bool setSyncWord(uint8_t sw);
    virtual uint8_t getSyncWord();
    // set the CRC mode
    virtual bool setCRC(bool enabled);
    virtual bool getCRC();
    // set the IQ inversion mode
    virtual bool setInvertIQ(bool enabled);
    virtual bool getInvertIQ();
    // set the Low Data Rate Optimization mode
    virtual bool setLowDataRateOptimize(bool enabled);
    virtual bool getLowDataRateOptimize();
};
