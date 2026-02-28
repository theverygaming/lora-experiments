#include <logging.h>
#include <variant.h>
#include <variant_common.h>
#include <SPI.h>
#include <RadioRFM95.h>

#define V_LORA_SPI_SCK 6
#define V_LORA_SPI_MISO 8
#define V_LORA_SPI_MOSI 10
#define V_LORA_SPI_CS 13
#define V_RFM95_DIO0 16
#define V_RFM95_RESET 5

static SPIClass lora_spi = SPIClass(HSPI);

LoRaRadio *variant_get_radio() {
    LOG_DEBUG("SPI init");
    lora_spi.begin(V_LORA_SPI_SCK, V_LORA_SPI_MISO, V_LORA_SPI_MOSI);
    LOG_DEBUG("SPI init done");

    LoRaRadio *radio = new RadioRFM95(
        &lora_spi,
        8E6,
        V_LORA_SPI_CS,
        V_RFM95_DIO0,
        V_RFM95_RESET
    );
    LOG_DEBUG("RFM95 constructured");

    if(!radio->init()) {
        LOG_ERROR("radio init failed");
        return nullptr;
    }

    return radio;
}
