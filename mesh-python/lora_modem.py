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

    def set_gain(self, gain: int):
        """
        0 = AGC, 1=min 10=max
        """
        raise NotImplementedError()

    def set_frequency(self, freq_hz: int) -> None:
        raise NotImplementedError()

    def set_spreading_factor(self, sf: int) -> None:
        raise NotImplementedError()

    def set_bandwidth(self, bandwidth: int) -> None:
        raise NotImplementedError()

    def set_coding_rate(self, coding_rate: int) -> None:
        """
        Coding rate 4/x
        """
        raise NotImplementedError()

    def set_preamble_length(self, bits: int) -> None:
        raise NotImplementedError()

    def set_syncword(self, syncword: int) -> None:
        raise NotImplementedError()

    def set_tx_power(self, tx_power: int) -> None:
        raise NotImplementedError()

    def set_aux_lora_settings(
        self,
        crc: bool,
        invert_iq: bool,
        low_data_rate_optimize: bool,
    ):
        raise NotImplementedError()
