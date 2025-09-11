#include <LoRa.h> // https://github.com/sandeepmistry/arduino-LoRa - I was using RadioHead but it doesn't offer all the features I need
#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <FS.h>
#include <ArduinoJson.h>

#define MAX_PACKET_LEN  255
#define RX_QUEUE_SIZE   5

struct Packet {
  uint8_t len;
  uint8_t data[MAX_PACKET_LEN];
  int16_t rssi;       // RSSI of the received packet
  int16_t freqError;  // Frequency error in Hz
  int8_t snr;         // SNR of packet
};

Packet rxQueue[RX_QUEUE_SIZE];
uint8_t rxHead = 0;  // next write
uint8_t rxTail = 0;  // next read

bool queueFull() {
  return ((rxHead + 1) % RX_QUEUE_SIZE) == rxTail;
}

bool queueEmpty() {
  return rxHead == rxTail;
}

void enqueuePacket(uint8_t* buf, uint8_t len) {
  if (queueFull()) { // drop packet if full
    Serial.println("RX queue full!");
    return;
  }
  memcpy(rxQueue[rxHead].data, buf, len);
  rxQueue[rxHead].len = len;
  rxQueue[rxHead].rssi = LoRa.packetRssi();;
  rxQueue[rxHead].freqError = LoRa.packetFrequencyError();
  rxQueue[rxHead].snr = LoRa.packetSnr();
  rxHead = (rxHead + 1) % RX_QUEUE_SIZE;
}

bool dequeuePacket(Packet &p) {
  if (queueEmpty()) return false;
  p = rxQueue[rxTail];
  rxTail = (rxTail + 1) % RX_QUEUE_SIZE;
  return true;
}

WiFiClient wifiClient;
ESP8266WebServer server(80);

// ===== Global config =====
struct Config {
  String wifiSSID;
  String wifiPassword;
} config;

const char* configFile = "/config.json";

// ===== Load config from flash =====
void loadConfig() {
  if (!SPIFFS.begin()) {
    Serial.println("Failed to mount FS");
    return;
  }
  if (!SPIFFS.exists(configFile)) {
    Serial.println("No saved config");
    return;
  }

  File f = SPIFFS.open(configFile, "r");
  if (!f) {
    Serial.println("Failed to open config file");
    return;
  }

  StaticJsonDocument<512> doc;
  if (deserializeJson(doc, f)) {
    Serial.println("Failed to parse config, using defaults");
  } else {
    config.wifiSSID     = doc["wifiSSID"].as<String>();
    config.wifiPassword = doc["wifiPassword"].as<String>();
  }

  f.close();
}

// ===== Save config to flash =====
void saveConfig() {
  File f = SPIFFS.open(configFile, "w");
  if (!f) {
    Serial.println("Failed to open config file for writing");
    return;
  }

  StaticJsonDocument<512> doc;
  doc["wifiSSID"]     = config.wifiSSID;
  doc["wifiPassword"] = config.wifiPassword;

  serializeJson(doc, f);
  f.close();

  Serial.println("Config saved to flash");
}

// ===== Serial config prompt =====
void promptConfig() {
  Serial.println("\n=== Configuration ===");

  Serial.print("WiFi SSID [" + config.wifiSSID + "]: ");
  while (!Serial.available()) delay(10);
  String ssid = Serial.readStringUntil('\n');
  if (ssid.length() > 0) config.wifiSSID = ssid;

  Serial.print("WiFi Password [" + config.wifiPassword + "]: ");
  while (!Serial.available()) delay(10);
  String pass = Serial.readStringUntil('\n');
  if (pass.length() > 0) config.wifiPassword = pass;

  saveConfig();
}

// ===== WiFi connect =====
void connectWiFi() {
  Serial.println("Connecting to WiFi...");
  WiFi.begin(config.wifiSSID.c_str(), config.wifiPassword.c_str());
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 20) {
    delay(500);
    Serial.print(".");
    retries++;
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected: " + WiFi.localIP().toString());
  } else {
    Serial.println("Failed to connect to WiFi");
  }
}

// Encode uint8_t array to JSON array
void bytesToJsonArray(const uint8_t* data, uint8_t len, JsonArray arr) {
  for (uint8_t i = 0; i < len; i++) {
    arr.add(data[i]);
  }
}

// Decode JSON array to byte array
bool jsonArrayToBytes(JsonArray arr, uint8_t* buf, uint8_t maxLen, uint8_t &outLen) {
  outLen = 0;
  for (JsonVariant v : arr) {
    if (!v.is<unsigned int>()) return false;
    if (outLen >= maxLen) return false;
    buf[outLen++] = (uint8_t)v.as<unsigned int>();
  }
  return true;
}

void handleRx() {
  StaticJsonDocument<512> doc;
  JsonArray arr = doc.createNestedArray("packet");

  Packet p;
  if (dequeuePacket(p)) {
    JsonObject obj = doc.createNestedObject("packet");
    JsonArray arr = obj.createNestedArray("data");
    for (uint8_t i = 0; i < p.len; i++) arr.add(p.data[i]);
    obj["rssi"] = p.rssi;
    obj["freqError"] = p.freqError;
    obj["snr"] = p.snr;
  } else {
    doc["packet"] = false;
  }

  String json;
  serializeJson(doc, json);
  server.send(200, "application/json", json);
}

uint8_t txbuf[MAX_PACKET_LEN];

void handleTx() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"No body\"}");
    return;
  }

  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, server.arg("plain"));
  if (err) {
    server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
    return;
  }

  if (!doc.containsKey("packet") || !doc["packet"].is<JsonArray>()) {
    server.send(400, "application/json", "{\"error\":\"Missing or invalid 'packet' array\"}");
    return;
  }

  JsonArray arr = doc["packet"];
  uint8_t len = 0;
  if (!jsonArrayToBytes(arr, txbuf, sizeof(txbuf), len)) {
    server.send(400, "application/json", "{\"error\":\"Packet too long or invalid\"}");
    return;
  }

  LoRa.beginPacket();
  LoRa.write(txbuf, len);
  LoRa.endPacket();

  // Return success state
  StaticJsonDocument<128> res;
  res["success"] = true;
  String json;
  serializeJson(res, json);
  server.send(200, "application/json", json);

  Serial.printf("LoRa TX: len=%d\n", len);
}

void handlePostConfig() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"No body\"}");
    return;
  }

  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, server.arg("plain"));
  if (err) {
    server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
    return;
  }

  // Only update fields that exist
  if (doc.containsKey("frequency")) {
    int freq = doc["frequency"].as<int>();
    LoRa.setFrequency(freq);
    Serial.println("Set frequency: " + String(freq));
  }

  if (doc.containsKey("spreadingFactor")) {
    int sf = doc["spreadingFactor"].as<int>();
    LoRa.setSpreadingFactor(sf);
    Serial.println("Set spreading factor: " + String(sf));
  }

  if (doc.containsKey("bandwidth")) {
    int bw = doc["bandwidth"].as<int>();
    LoRa.setSignalBandwidth(bw);
    Serial.println("Set bandwidth: " + String(bw));
  }

  if (doc.containsKey("codingRate4")) {
    int cr = doc["codingRate4"].as<int>();
    LoRa.setCodingRate4(cr);
    Serial.println("Set coding rate: 4/" + String(cr));
  }

  if (doc.containsKey("preambleLength")) {
    int pl = doc["preambleLength"].as<int>();
    LoRa.setPreambleLength(pl);
    Serial.println("Set preamble length: " + String(pl));
  }

  if (doc.containsKey("txPower")) {
    int txp = doc["txPower"].as<int>();
    LoRa.setTxPower(txp);
    Serial.println("Set TX power: " + String(txp));
  }

  if (doc.containsKey("payloadCRC")) {
    bool crc = doc["payloadCRC"].as<bool>();
    if(crc) {
      LoRa.enableCrc();
    } else {
      LoRa.disableCrc();
    }
    Serial.println("Set payload CRC: " + String(crc));
  }

  if (doc.containsKey("syncWord")) {
    int sw = doc["syncWord"].as<int>();
    LoRa.setSyncWord(sw);
    Serial.println("Set sync word: " + String(sw));
  }

  if (doc.containsKey("gain")) {
    int gain = doc["gain"].as<int>();
    LoRa.setGain(gain);
    Serial.println("Set gain: " + String(gain));
  }

  server.send(200, "application/json", "{\"status\":\"LoRa config updated\"}");
}

uint8_t loraRxBuf[MAX_PACKET_LEN];

void pollLora() {
  int len = LoRa.parsePacket();
  if (len) {
    Serial.println("LoRa RX, len=" + String(len));
    for (int i = 0; i < len; i++) {
      loraRxBuf[i] = LoRa.read();
    }
    enqueuePacket(loraRxBuf, len);
  }
}

// ===== Setup =====
void setup() {
  Serial.begin(115200);
  delay(200);

  Serial.println("Hii :3");

  // SS, DIO0
  // 15 -> D8, 5 -> D1
  LoRa.setPins(15, -1, 5);

  Serial.println("Initializing RFM95");
  if (!LoRa.begin(869525000)) {
    Serial.println("RFM95 init FAILED");
    delay(5000);
    ESP.restart();
  }

  // standard LoRa settings
  LoRa.setSpreadingFactor(11);
  LoRa.setSignalBandwidth(250000);
  LoRa.setCodingRate4(5);

  // advanced LoRa settings
  LoRa.setPreambleLength(16);
  LoRa.setSyncWord(0x2b); // meshtastic
  LoRa.setTxPower(2); // 2dBm
  LoRa.enableCrc();

  loadConfig();

  // Check if user wants to force config
  Serial.println("Press 'C' within 5 seconds to enter configuration mode...");
  unsigned long start = millis();
  bool forceConfig = false;
  while (millis() - start < 5000) {
    if (Serial.available()) {
      char c = Serial.read();
      if (c == 'C' || c == 'c') {
        Serial.readStringUntil('\n'); // consume newline
        forceConfig = true;
        break;
      }
    }
    delay(50);
  }

  // If config is missing or forced, prompt user
  if (forceConfig || config.wifiSSID.length() == 0) {
    promptConfig();
  }

  connectWiFi();

  server.on("/rx", HTTP_GET, handleRx);
  server.on("/tx", HTTP_POST, handleTx);
  server.on("/config", HTTP_POST, handlePostConfig);
  server.begin();
  Serial.println("HTTP server started");

  Serial.println("setup done!");
}

void loop() {
  server.handleClient();
  pollLora();
}
