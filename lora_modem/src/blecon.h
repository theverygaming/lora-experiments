#pragma once
#include <variant.h>

#ifdef USE_BLE
void blecon_init();
void blecon_loop();
#endif
