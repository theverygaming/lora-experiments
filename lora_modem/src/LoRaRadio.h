#pragma once
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
    // continuous receive mode, used together with onReceive
    virtual void modeContinousReceive();
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
    // returns maximum gain value
    virtual unsigned short getGainMax();
    // set TX power in dBm
    virtual bool setTxPower(unsigned short dbm);
    // returns the maximum possible TX power in dBm
    virtual unsigned short getTxPowerMax();
    // set the frequency in Hz
    virtual bool setFrequency(unsigned long frequencyHz);
    // set the LoRa Spreading Factor
    virtual bool setSpreadingFactor(unsigned short sf);
    // set the bandwidth in Hz
    virtual bool setSignalBandwidth(unsigned long sbw);
    // set the Coding Rate (4/denominator)
    virtual bool setCodingRate4(unsigned short denominator);
    // sets the preamble length in bits
    virtual bool setPreambleLength(unsigned short length);
    // sets the sync word
    virtual bool setSyncWord(uint8_t sw);
    // set the CRC mode
    virtual bool setCRC(bool enabled);
    // set the IQ inversion mode
    virtual bool setInvertIQ(bool enabled);
    // set the Low Data Rate Optimization mode
    virtual bool setLowDataRateOptimize(bool enabled);
};
