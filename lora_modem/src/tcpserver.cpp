#include <tcpserver.h>
#include <logging.h>
#include <cmdcon.h>
#include <variant.h>

#ifndef PLATFORM_PORTDUINO

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
        LOG_DEBUG("wifi status changed to %d", wifi_status);
        LOG_DEBUG("wifi IP: %s", WiFi.localIP().toString().c_str());
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

#else
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <fcntl.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/ioctl.h>

class SocketStream : public Stream {
private:
    int fd;

public:
    SocketStream(int fd) {
        this->fd = fd;
    }

    int available() override {
        int count = 0;
        ioctl(this->fd, FIONREAD, &count);
        return count;
    }

    int read() override {
        uint8_t b;
        int r = recv(this->fd, &b, 1, 0);

        if (r <= 0) {
            return -1;
        }
        return b;
    }

    int peek() override {
        uint8_t b;
        int r = recv(this->fd, &b, 1, MSG_PEEK);

        if (r <= 0) {
            return -1;
        }
        return b;
    }

    void flush() override {}

    size_t write(uint8_t b) override {
        return send(this->fd, &b, 1, 0);
    }

    size_t write(const uint8_t *buf, size_t size) override {
        return send(this->fd, buf, size, 0);
    }
};

static int server_fd = -1;
static int client_fd = -1;
static SocketStream *client_stream = nullptr;

static void fd_set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags < 0) flags = 0;
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

void tcpserver_init() {
    LOG_DEBUG("initializing TCP server");
    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        LOG_ERROR("TCP Server failed to create socket");
        return;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(8000);
    addr.sin_addr.s_addr = INADDR_ANY;

    if (bind(server_fd, (sockaddr*)&addr, sizeof(addr)) < 0) {
        LOG_ERROR("TCP Server bind failed");
        close(server_fd);
        server_fd = -1;
        return;
    }

    if (listen(server_fd, 1) < 0) {
        LOG_ERROR("TCP Server listen failed");
        close(server_fd);
        server_fd = -1;
        return;
    }

    fd_set_nonblocking(server_fd);
    LOG_DEBUG("initialized TCP server");
}

void tcpserver_loop() {
    if (server_fd < 0) {
        return;
    }
    if (client_fd < 0) {

        sockaddr_in client_addr{};
        socklen_t len = sizeof(client_addr);

        int client = accept(server_fd, (sockaddr*)&client_addr, &len);

        if (client >= 0) {
            fd_set_nonblocking(client);
            client_fd = client;

            LOG_INFO("new TCP client connected from %s", inet_ntoa(client_addr.sin_addr));

            client_stream = new SocketStream(client_fd);
            CMDConGlobal.set_stream(client_stream, nullptr);
        }
    } else {

        char buf;
        int r = recv(client_fd, &buf, 1, MSG_PEEK);

        if (r == 0) {
            LOG_INFO("TCP client disconnected");
            CMDConGlobal.set_stream(nullptr, nullptr);
            close(client_fd);
            client_fd = -1;
            delete client_stream;
            client_stream = nullptr;
        }
    }
}
#endif
