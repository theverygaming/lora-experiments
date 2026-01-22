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
