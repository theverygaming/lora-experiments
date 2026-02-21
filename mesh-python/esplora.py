import logging
import datetime
import threading
import json
import socket
from . import lora_modem
import time
import serial

_logger = logging.getLogger(__name__)

class ESPLoraBase(lora_modem.LoraModem):
    def __init__(self):
        super().__init__()
        self._settings_data = {
            "type": "settings",
            "receive": True,
        }
        self._running = False
        self._rx_cb = None

    def _start(self, rx_cb):
        self._running = True
        self._rx_cb = rx_cb

    def _stop(self):
        self._running = False
        self._rx_cb = None

    def _tx_data(self, data):
        raise NotImplementedError()

    def _rx_data(self, data):
        if not data:
            return
        if data.get("type") not in ["telemetry"]:
            _logger.debug("rx from modem: %s", data)
        if data.get("type") != "packetRx":
            return
        try:
            self._rx_cb(lora_modem.LoraPacketReceived(
                data=bytes(data["data"]),
                rssi=data["rssi"],
                snr=data["snr"],
                freqError=data["freqError"],
            ))
        except:
            _logger.exception("rx_cb exception")

    def _tx(self, p: lora_modem.LoraPacket):
        data = {
            "type": "packetTx",
            "data": list(p.data),
            "cad": True,
            "cadWait": 2000,
            "cadTimeout": 10000,
        }
        _logger.debug("transmitting: %s", data)
        self._tx_data(data)

    def _set_lora_settings(self, vals: dict):
        for k, v in vals.items():
            self._settings_data[k] = v
        if self._running:
            _logger.debug("updating settings: %s", vals)
            self._tx_data({"type": "settings", **vals})

    def _set_lora_params(self, params):
        simple_param_map = {
            "frequency": "frequency",
            "spreading_factor": "spreadingFactor",
            "bandwidth": "signalBandwidth",
            "coding_rate": "codingRate4",
            "preamble_length": "preambleLength",
            "syncword": "syncWord",
            "tx_power": "txPower",
            "crc": "CRC",
            "invert_iq": "invertIQ",
            "low_data_rate_optimize": "lowDataRateOptimize",
        }
        res = {}
        for name, value in params.items():
            match name:
                case "gain":
                    if value != 0:
                        value = max(int((value * 6) / 10), 1)
                    res["gain"] = value
                case _:
                    res[simple_param_map[name]] = value
        self._set_lora_settings(res)


class ESPLoraWifi(ESPLoraBase):
    def __init__(self, host, port):
        super().__init__()
        self._host = host
        self._port = port
        self._sockfile = None
        self._rx_thread_stop = None

    def _tx_data(self, data):
        if self._sockfile is None:
            _logger.debug("no TX cuz no _sockfile")
            return
        self._sockfile.write(json.dumps(data) + "\n")
        self._sockfile.flush()

    def _start(self, rx_cb):
        def _conn_thread():
            while not self._rx_thread_stop.is_set():
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(15) # 15s timeout
                    sock.connect((self._host, self._port))
                    self._sockfile = sock.makefile("rw", encoding="utf-8", newline="\n")
                    self._tx_data(self._settings_data)
                    while not self._rx_thread_stop.is_set():
                        line = self._sockfile.readline()
                        try:
                            data = json.loads(line)
                            self._rx_data(data)
                        except:
                            _logger.debug("line causing error: %s", line)
                            _logger.exception("processing exception")
                except:
                    _logger.exception("exception")
                    self._sockfile = None
                    if sock is not None:
                        sock.close()
                    time.sleep(1) # don't immediately attempt to reconnect

        self._rx_thread_stop = threading.Event()
        self._rx_thread = threading.Thread(target=_conn_thread)
        self._rx_thread.start()
        super()._start(rx_cb)

    def _stop(self):
        self._rx_thread_stop.set()
        self._rx_thread.join()
        super()._stop()

class ESPLoraSerial(ESPLoraBase):
    def __init__(self, port):
        super().__init__()
        self._port = port
        self._serial_port = None
        self._rx_thread_stop = None

    def _tx_data(self, data):
        if self._serial_port is None:
            _logger.debug("no TX cuz no _serial_port")
            return
        self._serial_port.write((json.dumps(data) + "\n").encode("utf-8"))
        self._serial_port.flush()

    def _start(self, rx_cb):
        def _conn_thread():
            while not self._rx_thread_stop.is_set():
                sock = None
                try:
                    self._serial_port = serial.Serial(port=self._port, baudrate=115200, bytesize=8, timeout=10, stopbits=serial.STOPBITS_ONE)
                    self._tx_data(self._settings_data)
                    while not self._rx_thread_stop.is_set():
                        line = self._serial_port.readline()
                        try:
                            data = json.loads(line)
                            self._rx_data(data)
                        except:
                            _logger.debug("line causing error: %s", line)
                            _logger.exception("processing exception")
                except:
                    _logger.exception("exception")
                    self._serial_port = None
                    if sock is not None:
                        sock.close()
                    time.sleep(1) # don't immediately attempt to reconnect

        self._rx_thread_stop = threading.Event()
        self._rx_thread = threading.Thread(target=_conn_thread)
        self._rx_thread.start()
        super()._start(rx_cb)

    def _stop(self):
        self._rx_thread_stop.set()
        self._rx_thread.join()
        super()._stop()
