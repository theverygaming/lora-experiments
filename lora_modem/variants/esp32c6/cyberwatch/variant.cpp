#include <logging.h>
#include <variant.h>
#include <variant_common.h>
#include <SPI.h>
#include <RadioSX1262.h>

#define V_LORA_SPI_SCK 19
#define V_LORA_SPI_MISO 20
#define V_LORA_SPI_MOSI 18

#define V_LORA_SPI_CS 0
#define V_SX1262_DIO1 21
#define V_SX1262_BUSY 4
#define V_SX1262_RESET 5


static SPIClass lora_spi = SPIClass(FSPI);

LoRaRadio *variant_get_radio() {
    LOG_DEBUG("SPI init");
    lora_spi.begin(V_LORA_SPI_SCK, V_LORA_SPI_MISO, V_LORA_SPI_MOSI);
    lora_spi.setFrequency(8000000);
    LOG_DEBUG("SPI init done");

    LOG_DEBUG("creating RadioLib radio");
    SX1262 *sx1262 = new SX1262(new Module(
        new ArduinoHal(lora_spi),
        V_LORA_SPI_CS,
        V_SX1262_DIO1,
        V_SX1262_RESET,
        V_SX1262_BUSY // busy = gpio apparently
    ));
    RadioSX1262 *radiosx1262 = new RadioSX1262(sx1262);
    LOG_DEBUG("done creating RadioLib radio");

    if(!radiosx1262->init()) {
        LOG_ERROR("radio init failed");
        return nullptr;
    }

    if (sx1262->setDio2AsRfSwitch(true) != RADIOLIB_ERR_NONE) {
        LOG_ERROR("could not set DIO2 as RF switch");
    }

    return radiosx1262;
}
