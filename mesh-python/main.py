import traceback
import time
import json
import esplora
import meshtastic_dm


def meshtastic_stuff():
    # channels.json is a list of objects with the keys name and psk
    with open("channels.json") as f:
        channels_json = json.loads(f.read())

    meshtastic = meshtastic_dm.MeshtasticProto(lambda x: esplora.tx_packet(list(x)), channels_json)

    def rx_cb(rx):
        print(rx)
        try:
            meshtastic.packet_rx(bytes(rx["data"]), rx["rssi"], rx["snr"])
        except:
            print("exception ingesting meshtastic packet")
            traceback.print_exc()

    esplora.set_rx_cb(rx_cb)

    while True:
        time.sleep(1)

if __name__ == "__main__":
    print("Sending config...")
    esplora.init()

    meshtastic_stuff()
