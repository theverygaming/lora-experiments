import logging
import datetime
import threading
import json
import socket
import lora_modem
import time
import serial

_logger = logging.getLogger(__name__)

class ESPLoraBase(lora_modem.LoraModem):
    def __init__(self):
        self._settings_data = {
            "type": "settings",
            "receive": True,
        }
        self._running = False
        self._rx_cb = None
    
    def start(self, rx_cb):
        self._running = True
        self._rx_cb = rx_cb

    def stop(self):
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

    def tx(self, p: lora_modem.LoraPacket):
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

    def _set_lora_setting(self, name, val):
        self._set_lora_settings({name: val})

    def set_gain(self, gain: int):
        """
        0 = AGC, 1=min 10=max
        """
        # scale from 1-10 to 1-6
        if gain != 0:
            gain = max(int((gain * 6) / 10), 1)
        self._set_lora_setting("gain", gain)

    def set_frequency(self, freq_hz: int) -> None:
        self._set_lora_setting("frequency", freq_hz)

    def set_spreading_factor(self, sf: int) -> None:
        self._set_lora_setting("spreadingFactor", sf)

    def set_bandwidth(self, bandwidth: int) -> None:
        self._set_lora_setting("signalBandwidth", bandwidth)

    def set_coding_rate(self, coding_rate: int) -> None:
        """
        Coding rate 4/x
        """
        self._set_lora_setting("codingRate4", coding_rate)

    def set_preamble_length(self, bits: int) -> None:
        self._set_lora_setting("preambleLength", bits)

    def set_syncword(self, syncword: int) -> None:
        self._set_lora_setting("syncWord", syncword)

    def set_tx_power(self, tx_power: int) -> None:
        self._set_lora_setting("txPower", tx_power)

    def set_aux_lora_settings(
        self,
        crc: bool,
        invert_iq: bool,
        low_data_rate_optimize: bool,
    ):
        self._set_lora_settings({
            "CRC": crc,
            "invertIQ": invert_iq,
            "lowDataRateOptimize": low_data_rate_optimize,
        })

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

    def start(self, rx_cb):
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
        super().start(rx_cb)

    def stop(self):
        self._rx_thread_stop.set()
        self._rx_thread.join()
        super().stop()

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

    def start(self, rx_cb):
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
        super().start(rx_cb)

    def stop(self):
        self._rx_thread_stop.set()
        self._rx_thread.join()
        super().stop()
