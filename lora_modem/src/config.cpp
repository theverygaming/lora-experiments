#include <config.h>
#include <logging.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <variant.h>

#if defined(ESP32)
#include <WiFi.h>
#elif defined(ARDUINO_ARCH_ESP8266)
#include <ESP8266WiFi.h>
#endif

static const char *config_file = "/config.json";

static JsonDocument config_read() {
    JsonDocument doc;
    File file = LittleFS.open(config_file, "r");
    if(!file) {
        LOG_ERROR("failed to open config file");
        return doc;
    }
    DeserializationError error = deserializeJson(doc, file);
    if (error) {
        LOG_ERROR("config_read: deserializeJson() failed: %s", error.f_str());
        file.close();
        return doc;
    }
    file.close();
    return doc;
}

static void config_write(JsonDocument &doc) {
    File file = LittleFS.open(config_file, "w");
    if (!file) {
        LOG_ERROR("failed to open config file for (create) & write");
    }
    serializeJson(doc, file);
    file.close();
}

static void config_reset() {
    LOG_DEBUG("config_reset()");
    JsonDocument doc;
    config_write(doc);
}

static void config_reinit_wifi(JsonDocument &doc) {
    LOG_DEBUG("config_reinit_wifi()");
    #ifdef USE_WIFI
    if (doc["wifi"].is<JsonObject>() && doc["wifi"]["ssid"].is<const char *>() && doc["wifi"]["password"].is<const char *>()) {
        const char *ssid = doc["wifi"]["ssid"];
        const char *password = doc["wifi"]["password"];
        LOG_INFO("connecting to WiFi SSID: %s", ssid);
        WiFi.begin(ssid, password);
    }
    #endif
}

void config_init() {
    LOG_DEBUG("config_init()");
    if (!LittleFS.exists(config_file)) {
        LOG_INFO("no config file found, creating new one");
        config_reset();
    }

#if defined(ESP32) && defined(USE_WIFI)
    WiFi.onEvent([](WiFiEvent_t event, WiFiEventInfo_t info){
        static WiFiEvent_t ev_prev = (WiFiEvent_t)0;
        if (event == ev_prev) {
            return;
        }
        ev_prev = event;
        switch (event) {
            case ARDUINO_EVENT_WIFI_READY:
                LOG_DEBUG("WiFi event: WiFi interface ready");
                break;
            case ARDUINO_EVENT_WIFI_SCAN_DONE:
                LOG_DEBUG("WiFi event: Completed scan for access points");
                break;
            case ARDUINO_EVENT_WIFI_STA_START:
                LOG_DEBUG("WiFi event: WiFi client started");
                break;
            case ARDUINO_EVENT_WIFI_STA_STOP:
                LOG_DEBUG("WiFi event: WiFi clients stopped");
                break;
            case ARDUINO_EVENT_WIFI_STA_CONNECTED:
                LOG_DEBUG("WiFi event: Connected to access point");
                break;
            case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
                LOG_DEBUG("WiFi event: Disconnected from WiFi access point reason: %d", info.wifi_sta_disconnected.reason);
                break;
            case ARDUINO_EVENT_WIFI_STA_AUTHMODE_CHANGE:
                LOG_DEBUG("WiFi event: Authentication mode of access point has changed");
                break;
            case ARDUINO_EVENT_WIFI_STA_GOT_IP:
                LOG_DEBUG("WiFi event: Obtained IP address: %s", WiFi.localIP().toString().c_str());
                break;
            case ARDUINO_EVENT_WIFI_STA_LOST_IP:
                LOG_DEBUG("WiFi event: Lost IP address and IP address is reset to 0");
                break;
            default:
                LOG_DEBUG("WiFi event: unknown event: %d", event);
                break;
        }
    });
#endif

    config_refresh();
    LOG_DEBUG("config initialized");
}

void config_set_wifi(const char *ssid, const char *password) {
    LOG_DEBUG("config_set_wifi(%s, ***)", ssid);
#ifdef USE_WIFI
    JsonDocument doc = config_read();
    JsonObject obj = doc["wifi"].to<JsonObject>();
    obj["ssid"] = ssid;
    obj["password"] = password;
    config_write(doc);
#endif
}

void config_refresh() {
    LOG_DEBUG("config_refresh()");
    JsonDocument doc = config_read();
#ifdef USE_WIFI
    config_reinit_wifi(doc);
#endif
}
