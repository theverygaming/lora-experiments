import time
import json
import esplora
import meshtastic_dm
import logging
import lora_modem

_logger = logging.getLogger(__name__)

def meshtastic_stuff(esplora_inst):
    # channels.json is a list of objects with the keys name and psk
    with open("channels.json") as f:
        channels_json = json.loads(f.read())

    esplora_inst.set_lora_settings(
        gain=0, # AGC
        frequency=869525000,
        spreading_factor=11,
        bandwidth=250000,
        coding_rate_4=5,
        preable_length=16,
        syncword=0x2b, # meshtastic
        tx_power=20,
        crc=True,
        invert_iq=False,
        low_data_rate_optimize=False,
    )

    meshtastic = meshtastic_dm.MeshtasticProto(lambda x: esplora_inst.tx(lora_modem.LoraPacket(data=x)), channels_json)

    def rx_cb(p):
        _logger.debug("rx_cb: %s", p)
        try:
            meshtastic.packet_rx(p.data, p.rssi, p.snr)
        except:
            _logger.exception("exception ingesting meshtastic packet")

    esplora_inst.start(rx_cb)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.DEBUG
    )

    esplora_inst = esplora.ESPLora(host="10.40.128.33", port=8000)

    meshtastic_stuff(esplora_inst)

    while True:
        time.sleep(1)
