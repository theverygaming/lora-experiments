import time
import json
import esplora
import meshtastic_dm
import logging

_logger = logging.getLogger(__name__)

def meshtastic_stuff():
    # channels.json is a list of objects with the keys name and psk
    with open("channels.json") as f:
        channels_json = json.loads(f.read())

    meshtastic = meshtastic_dm.MeshtasticProto(lambda x: esplora.tx_packet(list(x)), channels_json)

    def rx_cb(rx):
        _logger.debug("rx_cb: %s", rx)
        try:
            meshtastic.packet_rx(bytes(rx["data"]), rx["rssi"], rx["snr"])
        except:
            _logger.exception("exception ingesting meshtastic packet")

    esplora.set_rx_cb(rx_cb)

    while True:
        time.sleep(1)

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.DEBUG
    )
    esplora.init()

    meshtastic_stuff()
