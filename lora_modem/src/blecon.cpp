#include <blecon.h>
#include <cmdcon.h>
#include <logging.h>

#ifdef USE_BLE
// FIXME: the authentication here uhh probably doesn't fucking work lmfao this is more like a POC
// you should probably NEVER enable this code on any device that also does wifi in it's current state lmfao (you may leak ur wifi creds)
#include <NimBLEDevice.h>

#define UUID_SERVICE "6c899325-3f6d-4b1a-afac-87f2bef8b041"
#define UUID_READ "b2ad4cb8-32bf-443a-a7a8-9384fb18abb8"
#define UUID_WRITE "dc71cbf6-edc8-44d8-9648-ca26c3b76e6c"

static NimBLEServer *pServer;

class BLEStream : public Stream {
  NimBLECharacteristic *readCharacteristic;
  NimBLECharacteristic *writeCharacteristic;
  std::vector<uint8_t> buffer_rx;
  std::vector<uint8_t> buffer_tx;
  size_t mtu = 20;

public:
  BLEStream(NimBLECharacteristic *readCharacteristic,
            NimBLECharacteristic *writeCharacteristic)
      : readCharacteristic(readCharacteristic),
        writeCharacteristic(writeCharacteristic) {}

  int available() override { return buffer_rx.size(); }

  int read() override {
    if (buffer_rx.empty()) {
      return -1;
    }
    uint8_t val = buffer_rx.front();
    buffer_rx.erase(buffer_rx.begin());
    return val;
  }

  int peek() override {
    if (buffer_rx.empty()) {
      return -1;
    }
    return buffer_rx.front();
  }

  void flush() override {
    while (!buffer_tx.empty()) {
      size_t chunkSize = std::min(buffer_tx.size(), mtu);
      std::vector<uint8_t> chunk;
      for (size_t i = 0; i < chunkSize; i++) {
        chunk.push_back(buffer_tx.front());
        buffer_tx.erase(buffer_tx.begin());
      }
      if (readCharacteristic) {
        readCharacteristic->setValue(chunk.data(), chunk.size());
        readCharacteristic->notify();
      }
      delay(1); // let BLE cook
    }
  }

  size_t write(uint8_t b) override {
    buffer_tx.push_back(b);
    bool do_flush = b == '\n';
    if (buffer_tx.size() >= mtu || do_flush) {
      flush();
    }
    return 1;
  }

  size_t write(const uint8_t *buf, size_t size) override {
    bool do_flush = false;
    for (size_t i = 0; i < size; i++) {
      buffer_tx.push_back(buf[i]);
      do_flush |= buf[i] == '\n';
    }
    if (buffer_tx.size() >= mtu || do_flush) {
      flush();
    }
    return size;
  }

  void dataReceived() {
    if (!writeCharacteristic)
      return;
    std::string val = writeCharacteristic->getValue();
    buffer_rx.insert(buffer_rx.end(), val.begin(), val.end());
  }

  void connected() {
    buffer_rx.clear();
    buffer_tx.clear();
  }

  void setMTU(size_t mtu) { this->mtu = mtu; }
};

static BLEStream *bleStream = nullptr;

class ServerCallbacks : public NimBLEServerCallbacks {
  void onConnect(NimBLEServer *pServer, NimBLEConnInfo &connInfo) override {
    LOG_DEBUG("Client address: %s", connInfo.getAddress().toString().c_str());

    /**
     *  We can use the connection handle here to ask for different connection
     * parameters. Args: connection handle, min connection interval, max
     * connection interval latency, supervision timeout. Units; Min/Max
     * Intervals: 1.25 millisecond increments. Latency: number of intervals
     * allowed to skip. Timeout: 10 millisecond increments.
     */
    pServer->updateConnParams(connInfo.getConnHandle(), 24, 48, 0, 180);
  }

  void onDisconnect(NimBLEServer *pServer, NimBLEConnInfo &connInfo,
                    int reason) override {
    LOG_DEBUG("Client disconnected - start advertising");
    NimBLEDevice::startAdvertising();
  }

  void onMTUChange(uint16_t MTU, NimBLEConnInfo &connInfo) override {
    LOG_DEBUG("MTU updated: %u for connection ID: %u", MTU,
              connInfo.getConnHandle());
    bleStream->setMTU(MTU - 3); // - 3 cuz BLE overhead
  }

} serverCallbacks;

class CharacteristicCallbacks : public NimBLECharacteristicCallbacks {
  void onWrite(NimBLECharacteristic *pCharacteristic,
               NimBLEConnInfo &connInfo) override {
    bleStream->dataReceived();
  }

  /** Peer subscribed to notifications/indications */
  void onSubscribe(NimBLECharacteristic *pCharacteristic,
                   NimBLEConnInfo &connInfo, uint16_t subValue) override {
    std::string str = "Client ID: ";
    str += connInfo.getConnHandle();
    str += " Address: ";
    str += connInfo.getAddress().toString();
    if (subValue == 0) {
      str += " Unsubscribed to ";
    } else if (subValue == 1) {
      str += " Subscribed to notifications for ";
    } else if (subValue == 2) {
      str += " Subscribed to indications for ";
    } else if (subValue == 3) {
      str += " Subscribed to notifications and indications for ";
    }
    str += std::string(pCharacteristic->getUUID());

    LOG_DEBUG("%s", str.c_str());

    if (subValue == 0) {
      CMDConGlobal.set_stream(nullptr, nullptr);
    } else {
      bleStream->setMTU(connInfo.getMTU() - 3); // - 3 cuz BLE overhead
      bleStream->connected();
      CMDConGlobal.set_stream(bleStream, nullptr);
    }
  }
} chrCallbacks;

void blecon_init() {
  LOG_DEBUG("initializing BLE");
  NimBLEDevice::init("NimBLE");
  LOG_DEBUG("setPower");
  NimBLEDevice::setPower(3); /** +3db */

  LOG_DEBUG("setSecurityAuth");
  NimBLEDevice::setSecurityAuth(
      true, true, false); /** bonding, MITM, don't need BLE secure connections
                             as we are using passkey pairing */
  LOG_DEBUG("setSecurityPasskey");
  NimBLEDevice::setSecurityPasskey(BLE_DEFAULT_PAIRING_CODE);
  LOG_DEBUG("setSecurityIOCap");
  NimBLEDevice::setSecurityIOCap(
      BLE_HS_IO_DISPLAY_ONLY); /** Display only passkey */
  LOG_DEBUG("createServer");
  pServer = NimBLEDevice::createServer();
  LOG_DEBUG("server setCallbacks");
  pServer->setCallbacks(&serverCallbacks);
  LOG_DEBUG("createService");
  NimBLEService *pService = pServer->createService(UUID_SERVICE);
  LOG_DEBUG("createCharacteristic");
  NimBLECharacteristic *pReadCharacteristic = pService->createCharacteristic(
      UUID_READ, NIMBLE_PROPERTY::READ | NIMBLE_PROPERTY::READ_AUTHEN |
                     NIMBLE_PROPERTY::READ_ENC | NIMBLE_PROPERTY::NOTIFY);
  LOG_DEBUG("createCharacteristic");
  NimBLECharacteristic *pWriteCharacteristic = pService->createCharacteristic(
      UUID_WRITE, NIMBLE_PROPERTY::WRITE | NIMBLE_PROPERTY::WRITE_AUTHEN |
                      NIMBLE_PROPERTY::WRITE_ENC);
  
  LOG_DEBUG("pService->start()");
  pService->start();
  
  LOG_DEBUG("setCallbacks read");
  pReadCharacteristic->setCallbacks(&chrCallbacks);
  LOG_DEBUG("setCallbacks write");
  pWriteCharacteristic->setCallbacks(&chrCallbacks);
  
  LOG_DEBUG("getAdvertising");
  NimBLEAdvertising *pAdvertising = NimBLEDevice::getAdvertising();
  LOG_DEBUG("advertising setName");
  pAdvertising->setName("lora_modem");
  LOG_DEBUG("addServiceUUID");
  pAdvertising->addServiceUUID(pService->getUUID());
  LOG_DEBUG("enableScanResponse");
  pAdvertising->enableScanResponse(
      true); // FIXME: should not be strictly required, removing this line
             // should save power
  LOG_DEBUG("pAdvertising->start()");
  pAdvertising->start();
  
  LOG_DEBUG("BLEStream init");
  bleStream = new BLEStream(pReadCharacteristic, pWriteCharacteristic);
  LOG_DEBUG("BLE init done");
}

void blecon_loop() {}

#endif
