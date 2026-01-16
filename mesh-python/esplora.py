# nix-shell -p python313Packages.meshtastic -p python313Packages.cryptography

import logging
import datetime
import threading
import json
import socket

_logger = logging.getLogger(__name__)


HOST = "10.40.128.33"
PORT = 8000

settings_data = {
    "type": "settings",
    "receive": True,
    "gain": 0, # 0 = AGC
    "frequency": 869525000,
    "spreadingFactor": 11,
    "signalBandwidth": 250000,
    "codingRate4": 5,
    "preambleLength": 16,
    "syncWord": 0x2b,
    "txPower": 20,
    "CRC": True,
    "invertIQ": False,
    "lowDataRateOptimize": False,
}

_cb = lambda x: x
_sockfile = None

def _conn_thread():
    global _sockfile
    while True:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))
            _sockfile = sock.makefile("rw", encoding="utf-8", newline="\n")
            _sockfile.write(json.dumps(settings_data) + "\n")
            _sockfile.flush()
            while True:
                line = _sockfile.readline()
                try:
                    data = json.loads(line)
                    _logger.debug("rx from modem: %s", data)
                    if data.get("type") != "packetRx":
                        continue
                    _cb({
                        "data": data["data"],
                        "rssi": data["rssi"],
                        "snr": data["snr"],
                        "freqError": data["freqError"]
                    })
                except:
                    _logger.exception("processing exception")
        except (ConnectionResetError, BrokenPipeError):
            _logger.exception("socket exception")
            _sockfile = None
            if sock is not None:
                sock.close()

def init():
    t = threading.Thread(target=_conn_thread)
    t.start()

def set_rx_cb(cb):
    global _cb
    _cb = cb

def tx_packet(packet_bytes):
    if _sockfile is None:
        _logger.debug("no _sockfile")
        return
    data = {
        "type": "packetTx",
        "data": list(packet_bytes),
        "cad": True,
        "cadWait": 100,
        "cadTimeout": 2000,
    }
    _logger.debug("transmitting: %s", data)
    _sockfile.write(json.dumps(data) + "\n")
    _sockfile.flush()
