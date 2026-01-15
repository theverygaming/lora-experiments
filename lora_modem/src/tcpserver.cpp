#include <tcpserver.h>
#include <logging.h>
#include <cmdcon.h>

#if defined(ESP32)
#include <WiFi.h>
#elif defined(ARDUINO_ARCH_ESP8266)
#include <ESP8266WiFi.h>
#endif

static WiFiServer server(8000);

static WiFiClient active_client;

void tcpserver_init() {
    server.begin();
}

void tcpserver_loop() {
    if (!active_client || !active_client.connected()) {
        active_client = server.available();
        if (active_client && active_client.connected()) {
            LOG_INFO("new TCP client connected from %s", active_client.remoteIP().toString().c_str());
            CMDConGlobal.set_stream(&active_client);
        }
    }
}
