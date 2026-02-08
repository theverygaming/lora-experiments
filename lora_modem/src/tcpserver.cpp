#include <tcpserver.h>
#include <logging.h>
#include <cmdcon.h>
#include <variant.h>

#ifdef USE_WIFI
#if defined(ESP32)
#include <WiFi.h>
#elif defined(ARDUINO_ARCH_ESP8266)
#include <ESP8266WiFi.h>
#endif

static WiFiServer server(8000);

static WiFiClient active_client;

void tcpserver_init() {
    LOG_DEBUG("initializing TCP server");
    server.begin();
    LOG_DEBUG("initialized TCP server");
}

void tcpserver_loop() {
    static int wifi_status = -1;
    if (wifi_status != WiFi.status()) {
        wifi_status = WiFi.status();
        unsigned long v4 = WiFi.localIP().v4();
        unsigned int v4_1 = v4 & 0xFF;
        unsigned int v4_2 = (v4 >> 8) & 0xFF;
        unsigned int v4_3 = (v4 >> 16) & 0xFF;
        unsigned int v4_4 = (v4 >> 24) & 0xFF;
        LOG_DEBUG("wifi status changed to %d IPv4: %u.%u.%u.%u", wifi_status, v4_1, v4_2, v4_3, v4_4);
    }
    if (!active_client || !active_client.connected()) {
        active_client = server.accept();
        if (active_client && active_client.connected()) {
            LOG_INFO("new TCP client connected from %s", active_client.remoteIP().toString().c_str());
            CMDConGlobal.set_stream(&active_client, nullptr);
        }
    }
}
#endif
