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
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def tx(self, p: LoraPacket):
        raise NotImplementedError()
    
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
        raise NotImplementedError()
