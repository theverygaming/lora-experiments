# python -m mesh-python.dev
# while [ true ]; do python -m mesh-python.dev 2>&1 | tee -a mesh-python/mesh-python.log; done
import time
import json
import logging
from . import esplora
from . import meshtastic_dm
from . import lora_modem
from . import meshcore

_logger = logging.getLogger(__name__)

def meshtastic_stuff(esplora_inst):
    # channels.json is a list of objects with the keys name and psk
    with open("channels.json") as f:
        channels_json = json.loads(f.read())

    meshtastic_inst = meshtastic_dm.Meshtastic(esplora_inst, channels_json)
    meshtastic_inst.start()

def meshcore_stuff(esplora_inst):
    node = meshcore.meshcore.MeshcoreNode()
    pkts = [
        # group msg in #test
        "150D498F8642DE3C33CCAB4EBAA028D937E5DB6B97E1D456C81BCE119EA8DAF177E7D3FCE230EF298C56C2E06C942D1506E4D45D09846BB525FD3D5673B39660F94AFAEBF3CC70BE2C680ABD1C85A2BD643F44949B9748CC80228B6F4F79AABDB2AB8104882BD70367DD24CDD6D091A1B506",
        # advert with location
        "120056CBB26E9DE37E150F9FD087E01D266C21D30088A8C2DBDEFF4E6005726A796FB0D18569EEB69315DDBCFCBEAE402E09AFC9946F3F8BDE8A0477E9AB157865987D78BB1B3F55999C1107830375E5F6C904D5F81FE0A766A260B31BA53EFD03D1E54BFB05925AE739035A6C8F004D757368726F6F6D20F09F8D84202874656D7029",
        # trace
        "260334F6E3AA57517E0000000000D026B326D0",
    ]
    #for pkt in pkts:
        #_logger.info("decoded: %s", meshcore.meshcore.MeshcorePacket.deserialize(node, bytes.fromhex(pkt)))
    meshcore_inst = meshcore.meshcore.Meshcore(esplora_inst, node)
    meshcore_inst.start()

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.DEBUG
    )

    esplora_inst = esplora.ESPLoraWifi(host="10.40.189.193", port=8000)
    # esplora_inst = esplora.ESPLoraSerial("/dev/ttyACM0")

    # meshtastic_stuff(esplora_inst)
    meshcore_stuff(esplora_inst)

    while True:
        time.sleep(1)
