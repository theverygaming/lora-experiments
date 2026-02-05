#include <variant.h>
#include <logging.h>
#include <stdarg.h>
#include <Arduino.h>
#include <serialcon.h>
#include <cmdcon.h>

#ifndef SERIALCON_SERIAL_PORT
#define SERIALCON_SERIAL_PORT Serial
#endif

bool serialcon_cmd_mode = false;

void serialcon_init() {
    SERIALCON_SERIAL_PORT.begin(115200);
    // wait a few seconds for anything to connect, so the other side always gets all messages
    auto t = millis();
    while (!SERIALCON_SERIAL_PORT && millis() - t < 1000 * 5) {
        delay(10);
        yield();
    }
    serialcon_cmd_mode = false;
}

void serialcon_print(const char *str) {
    if (!serialcon_cmd_mode) {
        SERIALCON_SERIAL_PORT.print(str);
    }
}

void serialcon_println(const char *str) {
    if (!serialcon_cmd_mode) {
        SERIALCON_SERIAL_PORT.println(str);
    }
}

void serialcon_poll() {
    if (serialcon_cmd_mode) {
        return;
    }
    if (SERIALCON_SERIAL_PORT.available()) {
        serialcon_cmd_mode = true;
        CMDConGlobal.set_stream(
            &SERIALCON_SERIAL_PORT,
            [](){
                serialcon_cmd_mode = false;
                LOG_DEBUG("serial CMD mode disabled");
            }
        );
    }
}
