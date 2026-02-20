import dataclasses

@dataclasses.dataclass
class LoraPacket:
    data: bytes

@dataclasses.dataclass
class LoraPacketReceived(LoraPacket):
    snr: float # SNR (dB)
    rssi: int # RSSI (dBm)
    freqError: int # frequency error in Hz

class LoraModem:
    def start(self, rx_cb):
        self._start(rx_cb)

    def _start(self, rx_cb):
        raise NotImplementedError()

    def stop(self):
        self._stop()

    def _stop(self):
        raise NotImplementedError()

    def tx(self, p: LoraPacket):
        self._tx(p)

    def _tx(self, p: LoraPacket):
        raise NotImplementedError()

    def _set_lora_params(self, params):
        raise NotImplementedError()

    def set_gain(self, gain: int):
        """
        0 = AGC, 1=min 10=max
        """
        self._set_lora_params({"gain": gain})

    def set_frequency(self, freq_hz: int) -> None:
        self._set_lora_params({"frequency": freq_hz})

    def set_spreading_factor(self, sf: int) -> None:
        self._set_lora_params({"spreading_factor": sf})

    def set_bandwidth(self, bandwidth: int) -> None:
        self._set_lora_params({"bandwidth": bandwidth})

    def set_coding_rate(self, coding_rate: int) -> None:
        """
        Coding rate 4/x
        """
        self._set_lora_params({"coding_rate": coding_rate})

    def set_preamble_length(self, bits: int) -> None:
        self._set_lora_params({"preamble_length": bits})

    def set_syncword(self, syncword: int) -> None:
        self._set_lora_params({"syncword": syncword})

    def set_tx_power(self, tx_power: int) -> None:
        self._set_lora_params({"tx_power": tx_power})

    def set_aux_lora_settings(
        self,
        crc: bool,
        invert_iq: bool,
        low_data_rate_optimize: bool,
    ):
        self._set_lora_params({
            "crc": crc,
            "invert_iq": invert_iq,
            "low_data_rate_optimize": low_data_rate_optimize,
        })
