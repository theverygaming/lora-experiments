import traceback
import time
import json
import esplora
import meshtastic_dm

if __name__ == "__main__":
    print("Sending config...")
    esplora.send_config()

    # channels.json is a list of objects with the keys name and psk
    with open("channels.json") as f:
        channels_json = json.loads(f.read())

    meshtastic = meshtastic_dm.MeshtasticProto(lambda x: esplora.send_tx_packet(list(x)), channels_json)

    while True:
        for _ in range(30):
            rx = esplora.poll_rx()
            if rx:
                try:
                    meshtastic.packet_rx(bytes(rx["data"]), rx["rssi"], rx["snr"])
                except:
                    print("exception ingesting meshtastic packet")
                    traceback.print_exc()
            time.sleep(0.2)
