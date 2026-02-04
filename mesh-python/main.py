import time
import json
import esplora
import meshtastic_dm
import logging
import lora_modem
import meshcore

_logger = logging.getLogger(__name__)

def meshtastic_stuff(esplora_inst):
    # channels.json is a list of objects with the keys name and psk
    with open("channels.json") as f:
        channels_json = json.loads(f.read())

    meshtastic_inst = meshtastic_dm.Meshtastic(esplora_inst, channels_json)
    meshtastic_inst.start()

def meshcore_stuff(esplora_inst):
    meshcore_inst = meshcore.Meshcore(esplora_inst)
    meshcore_inst.start()

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.DEBUG
    )

    # esplora_inst = esplora.ESPLoraWifi(host="10.40.128.33", port=8000)
    esplora_inst = esplora.ESPLoraSerial("/dev/ttyACM0")

    # meshtastic_stuff(esplora_inst)
    meshcore_stuff(esplora_inst)

    while True:
        time.sleep(1)
