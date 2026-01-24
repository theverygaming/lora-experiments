import logging
import datetime
import threading
import json
import socket
import lora_modem

_logger = logging.getLogger(__name__)

class ESPLora(lora_modem.LoraModem):
    def __init__(self, host, port):
        self._host = host
        self._port = port
        self._settings_data = {
            "type": "settings",
            "receive": True,
        }
        self._sockfile = None
        self._rx_thread_stop = None

    def start(self, rx_cb):
        def _conn_thread():
            while not self._rx_thread_stop.is_set():
                sock = None
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((self._host, self._port))
                    # FIXME: figure out timeout properly
                    #sock.settimeout(30) # 30s timeout
                    self._sockfile = sock.makefile("rw", encoding="utf-8", newline="\n")
                    self._sockfile.write(json.dumps(self._settings_data) + "\n")
                    self._sockfile.flush()
                    while not self._rx_thread_stop.is_set():
                        line = self._sockfile.readline()
                        try:
                            data = json.loads(line)
                            _logger.debug("rx from modem: %s", data)
                            if data.get("type") != "packetRx":
                                continue
                            rx_cb(lora_modem.LoraPacketReceived(
                                data=bytes(data["data"]),
                                rssi=data["rssi"],
                                snr=data["snr"],
                                freqError=data["freqError"],
                            ))
                        except:
                            _logger.exception("processing exception")
                except (ConnectionResetError, BrokenPipeError):
                    _logger.exception("socket exception")
                    self._sockfile = None
                    if sock is not None:
                        sock.close()

        self._rx_thread_stop = threading.Event()
        self._rx_thread = threading.Thread(target=_conn_thread)
        self._rx_thread.start()

    def stop(self):
        self._rx_thread_stop.set()
        self._rx_thread.join()

    def tx(self, p: lora_modem.LoraPacket):
        if self._sockfile is None:
            _logger.debug("no TX cuz no _sockfile")
            return
        data = {
            "type": "packetTx",
            "data": list(p.data),
            "cad": True,
            "cadWait": 2000,
            "cadTimeout": 10000,
        }
        _logger.debug("transmitting: %s", data)
        self._sockfile.write(json.dumps(data) + "\n")
        self._sockfile.flush()

    def set_lora_settings(
        self,
        gain: int, # 0 = AGC, 1=min 10=max
        frequency: int,
        spreading_factor: int,
        bandwidth: int,
        coding_rate_4: int,
        preable_length: int,
        syncword: int,
        tx_power: int,
        crc: bool,
        invert_iq: bool,
        low_data_rate_optimize: bool,
    ):
        self._settings_data = {
            "type": "settings",
            "receive": True,
            "gain": gain, # 0 = AGC
            "frequency": frequency,
            "spreadingFactor": spreading_factor,
            "signalBandwidth": bandwidth,
            "codingRate4": coding_rate_4,
            "preambleLength": preable_length,
            "syncWord": syncword,
            "txPower": tx_power,
            "CRC": crc,
            "invertIQ": invert_iq,
            "lowDataRateOptimize": low_data_rate_optimize,
        }
        if self._sockfile is not None:
            self._sockfile.write(json.dumps(self._settings_data) + "\n")
