#include <logging.h>
#include <variant.h>
#include <variant_common.h>
#include <SPI.h>
#include <RadioRFM95.h>

#define V_LORA_SPI_CS 15
#define V_RFM95_DIO0 5
#define V_RFM95_RESET -1

static SPIClass lora_spi = SPIClass(SPI);

LoRaRadio *variant_get_radio() {
    LOG_DEBUG("SPI init");
    lora_spi.begin();
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
