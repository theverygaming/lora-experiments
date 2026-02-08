#include <variant.h>
#include <Arduino.h>
#include <SPI.h>
#include <logging.h>
#include <serialcon.h>
#include <cmdcon.h>
#include <LittleFS.h>
#include <config.h>
#include <tcpserver.h>
#include <blecon.h>

#ifdef USE_RFM95
#include <RadioRFM95.h>
#endif

LoRaRadio *radio = nullptr;

#if defined(ESP32)
#define LORA_SPI HSPI
#elif defined(ARDUINO_ARCH_ESP8266)
#define LORA_SPI SPI
#endif

static SPIClass lora_spi = SPIClass(LORA_SPI);

void setup() {
#ifdef HAS_LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);
#endif
    serialcon_init();
    LOG_INFO("hi from lora_modem!");
#if defined(ESP32)
    if(!LittleFS.begin(true /* formatOnFail */)) {
#elif defined(ARDUINO_ARCH_ESP8266)
    if(!LittleFS.begin()) {
#endif
        LOG_ERROR("could not initialize LittleFS, rebooting in 10s");
        delay(10*1000);
        ESP.restart();
    }
    config_init();

#ifdef USE_BLE
    blecon_init();
#endif

#ifdef USE_WIFI
    tcpserver_init();
#endif

    LOG_DEBUG("SPI init");
#if defined(ESP32)
    lora_spi.begin(LORA_SPI_SCK, LORA_SPI_MISO, LORA_SPI_MOSI);
#elif defined(ARDUINO_ARCH_ESP8266)
    lora_spi.begin();
#endif
    LOG_DEBUG("SPI init done");
#ifdef USE_RFM95
    if(radio == nullptr) {
        radio = new RadioRFM95(&lora_spi, 8E6, LORA_SPI_CS, RFM95_DIO0, RFM95_RESET);
        LOG_DEBUG("RFM95 constructured");
    }
#endif

    if(radio != nullptr && radio->init()) {
        LOG_INFO("Radio init OK");
    } else {
        LOG_ERROR("Radio init failed or no radio, rebooting in 10s");
        delay(10*1000);
        ESP.restart();
    }

    // random settings
    radio->setFrequency(868000000);
    radio->setSpreadingFactor(7);
    radio->setSignalBandwidth(125000);
    radio->setCodingRate4(5);
    radio->setPreambleLength(16);
    radio->setSyncWord(0x34);
    radio->setTxPower(1);
    radio->setCRC(true);

#ifdef HAS_LED
    digitalWrite(LED_PIN, LOW);
#endif
}

void loop() {
    static unsigned long prev_log = 0;
    if (millis() - prev_log > 5 * 1000) {
        prev_log = millis();
        LOG_DEBUG("loop");
    }

    serialcon_poll();

#ifdef USE_WIFI
    tcpserver_loop();
#endif

#ifdef USE_BLE
    blecon_loop();
#endif

    CMDConGlobal.process();

    delay(1);
}
