#include <logging.h>
#include <variant.h>
#include <variant_common.h>
#include <cstdlib>
#include <RadioSX1262.h>
#include <RadioLib.h>
#include <hal/RPi/PiHal.h>
#include <Wire.h>

/*
 * Blepis LoRa hat v2: 
 * Module is a Ra-01SCH-P (LLCC68)
 * SPI 1
 * CS: 17
 * DIO1: 23
 * Busy: 25
 * power, reset and stuff is on a GPIO expander, too lazy to document properly rn
 */

static void gpio_expander_init() {
    Wire.begin("/dev/i2c-1");

    // IO mask
    // set IO 7, 6, 5, 4, 3 as output, IO 0, 1, 2 as input
    // i2cset -y 1 0x20 0x00 0x07
    Wire.beginTransmission(0x20);
    Wire.write(0x00);
    Wire.write(0x07);
    Wire.endTransmission();

    // set IO 6, 5, 4 HIGH
    // i2cset -y 1 0x20 0x0a 0x70
    Wire.beginTransmission(0x20);
    Wire.write(0x0a);
    Wire.write(0x70);
    Wire.endTransmission();

    // wait a little to be verryyy sure chip is ready
    delay(100);

    // RESET
    // i2cset -y 1 0x20 0x0a 0x50
    Wire.beginTransmission(0x20);
    Wire.write(0x0a);
    Wire.write(0x50);
    Wire.endTransmission();
    // i2cset -y 1 0x20 0x0a 0x70
    Wire.beginTransmission(0x20);
    Wire.write(0x0a);
    Wire.write(0x70);
    Wire.endTransmission();
}

// FIXME: call this when the program is closed (signal handler?)
static void gpio_expander_deinit() {
    // i2cset -y 1 0x20 0x00 0xff
    Wire.beginTransmission(0x20);
    Wire.write(0x00);
    Wire.write(0xff);
    Wire.endTransmission();
    // i2cset -y 1 0x20 0x0a 0x00
    Wire.beginTransmission(0x20);
    Wire.write(0x0a);
    Wire.write(0x00);
    Wire.endTransmission();

    Wire.end();
}

static PiHal* hal = new PiHal(1);
static LLCC68 llcc68 = new Module(
    hal,
    17, // CS
    23, // DIO1
    RADIOLIB_NC, // reset - on GPIO expander, we reset on startup
    25 // busy
);

LoRaRadio *variant_get_radio() {
    gpio_expander_init();

    RadioSX1262 *radiosx1262 = new RadioSX1262(&llcc68);

    if(!radiosx1262->init()) {
        LOG_ERROR("radio init failed");
        return nullptr;
    }

    if (llcc68.setDio2AsRfSwitch(true) != RADIOLIB_ERR_NONE) {
        LOG_ERROR("could not set DIO2 as RF switch");
    }

    return nullptr;
}

void variant_restart() {
    gpio_expander_deinit();
    exit(0);
}
