import dataclasses
import math
import logging
import datetime
import math


_logger = logging.getLogger(__name__)


def calculate_airtime(
    spreading_factor: int,
    bandwidth: int,
    coding_rate_4: int,
    preamble_len: int,
    crc: bool,
    ldro: bool,
    with_header: bool,
    payload_bytes: int,
):
    # calculations from:
    # https://www.mobilefish.com/download/lora/lora_part17.pdf
    # https://www.rfwireless-world.com/calculators/lorawan-airtime-calculator
    # https://www.semtech.com/design-support/lora-calculator
    t_sym = ((2 ** spreading_factor) / bandwidth)
    t_preamble = (preamble_len + 4.25) * t_sym
    payload_data_syms = 8 * payload_bytes
    # this shit crazy lmao, I should make it more readable sometime...
    payload_syms = (
        8
        + max(
            math.ceil(
                (payload_data_syms - (4 * spreading_factor) + 28 + (16 if crc else 0) - (0 if with_header else 20))
                / (4 * (spreading_factor - (2 if ldro else 0)))
            ) * (coding_rate_4),
            0,
        )
    )
    t_payload = (payload_syms) * t_sym
    return t_preamble + t_payload


class DutyCycleTracker:
    def __init__(self, observed_max_secs, interval_secs):
        self._interval = interval_secs
        self._n_buckets = math.ceil(observed_max_secs / self._interval)
        self._buckets = [0.0] * self._n_buckets
        self._t_last = datetime.datetime.now().timestamp()

    def report(self, secs):
        if secs > self._interval:
            raise Exception("on time > interval time")

        tnow = datetime.datetime.now().timestamp()
        tdelta = tnow - self._t_last
        # when called at intervals smaller than self._interval, try to be accurate
        self._t_last = tnow - (tdelta % self._interval)

        # add buckets depending on the time elapsed
        self._buckets = ([0.0] * int(tdelta / self._interval)) + self._buckets

        # remove buckets outside the maximum observation time
        if len(self._buckets) - self._n_buckets > 0:
            del self._buckets[-(len(self._buckets) - self._n_buckets):]

        # actually add the on time to the current bucket
        self._buckets[0] += secs

    def get_duty(self, secs=None):
        if secs is None:
            secs = self._n_buckets * self._interval
        if secs < self._interval:
            raise Exception("asked for duty cycle in timeframe smaller than interval")
        n_buckets_sum = math.ceil(secs / self._interval)
        if n_buckets_sum > len(self._buckets):
            raise Exception("asked for time period larger than the maximum observal time")
        return sum(self._buckets[:n_buckets_sum]) / secs


@dataclasses.dataclass
class LoraPacket:
    data: bytes

@dataclasses.dataclass
class LoraPacketReceived(LoraPacket):
    snr: float # SNR (dB)
    rssi: int # RSSI (dBm)
    freqError: int # frequency error in Hz

class LoraModem:
    def __init__(self):
        self._spreading_factor = None
        self._bandwidth = None
        self._coding_rate = None
        self._preamble_length = None
        self._crc = None
        self._low_data_rate_optimize = None
        self._dt_rx = DutyCycleTracker(60*60, 60)
        self._dt_tx = DutyCycleTracker(60*60, 60)

    def _calc_airtime(self, packet: LoraPacket):
        for a in ["_spreading_factor", "_bandwidth", "_coding_rate", "_preamble_length", "_crc", "_low_data_rate_optimize"]:
            if getattr(self, a) is None:
                raise Exception(f"attr '{a}' required for _calc_airtime")
        return calculate_airtime(
            self._spreading_factor,
            self._bandwidth,
            self._coding_rate,
            self._preamble_length,
            self._crc,
            self._low_data_rate_optimize,
            True,
            len(packet.data),
        )

    def start(self, rx_cb):
        def wrapped_rx_cb(p):
            airtime = self._calc_airtime(p)
            self._dt_rx.report(airtime)
            _logger.debug("RX airtime: %fs", airtime)
            _logger.debug(
                "RX duty cycle: 1min: %f%% 10min: %f%% 60min: %f%%",
                self._dt_rx.get_duty(60) * 100,
                self._dt_rx.get_duty(60*10) * 100,
                self._dt_rx.get_duty(60*60) * 100,
            )
            rx_cb(p)
        self._start(wrapped_rx_cb)

    def _start(self, rx_cb):
        raise NotImplementedError()

    def stop(self):
        self._stop()

    def _stop(self):
        raise NotImplementedError()

    def tx(self, p: LoraPacket):
        airtime = self._calc_airtime(p)
        self._dt_tx.report(airtime)
        _logger.debug("TX airtime: %fs", airtime)
        _logger.debug(
            "TX duty cycle: 1min: %f%% 10min: %f%% 60min: %f%%",
            self._dt_tx.get_duty(60) * 100,
            self._dt_tx.get_duty(60*10) * 100,
            self._dt_tx.get_duty(60*60) * 100,
        )
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
        self._spreading_factor = sf
        self._set_lora_params({"spreading_factor": sf})

    def set_bandwidth(self, bandwidth: int) -> None:
        self._bandwidth = bandwidth
        self._set_lora_params({"bandwidth": bandwidth})

    def set_coding_rate(self, coding_rate: int) -> None:
        """
        Coding rate 4/x
        """
        self._coding_rate = coding_rate
        self._set_lora_params({"coding_rate": coding_rate})

    def set_preamble_length(self, bits: int) -> None:
        self._preamble_length = bits
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
        self._crc = crc
        self._low_data_rate_optimize = low_data_rate_optimize
        self._set_lora_params({
            "crc": crc,
            "invert_iq": invert_iq,
            "low_data_rate_optimize": low_data_rate_optimize,
        })
