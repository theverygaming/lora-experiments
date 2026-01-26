import logging
import datetime
import threading
import json
import socket
import lora_modem
import time

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
                    sock.settimeout(15) # 15s timeout
                    sock.connect((self._host, self._port))
                    self._sockfile = sock.makefile("rw", encoding="utf-8", newline="\n")
                    self._sockfile.write(json.dumps(self._settings_data) + "\n")
                    self._sockfile.flush()
                    while not self._rx_thread_stop.is_set():
                        line = self._sockfile.readline()
                        try:
                            data = json.loads(line)
                            if not data:
                                continue
                            if data.get("type") not in ["telemetry"]:
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
                except:
                    _logger.exception("exception")
                    self._sockfile = None
                    if sock is not None:
                        sock.close()
                    time.sleep(1) # don't immediately attempt to reconnect

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

    def _set_lora_settings(self, vals: dict):
        for k, v in vals.items():
            self._settings_data[k] = v
        if self._sockfile is not None:
            _logger.debug("updating settings: %s", vals)
            self._sockfile.write(json.dumps({"type": "settings", **vals}) + "\n")
            self._sockfile.flush()

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
