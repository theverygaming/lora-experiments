# nix-shell -p python313Packages.requests -p python313Packages.meshtastic -p python313Packages.cryptography

import requests
import time
import base64
from hashlib import sha256
import datetime
import meshtastic_dm
import traceback
import json

BASE_URL = "http://192.168.1.184/"


config_data = {
    "frequency": 869525000,
    "spreadingFactor": 11,
    "bandwidth": 250000,
    "codingRate4": 5,
    "preambleLength": 16,
    "txPower": 10,
    "payloadCRC": True,
    "syncWord": 0x2b,
    "gain": 0, # 0 = AGC
}


def send_config():
    url = f"{BASE_URL}/config"
    r = requests.post(url, json=config_data)
    if r.status_code == 200:
        print("Config sent successfully:", r.json())
    else:
        print("Failed to send config:", r.status_code, r.text)

def send_tx_packet(packet_bytes):
    url = f"{BASE_URL}/tx"
    # Convert bytes to JSON array
    print(f"sending {len(packet_bytes)} byte packet")
    packet_json = {"packet": list(packet_bytes)}
    r = requests.post(url, json=packet_json)
    if r.status_code == 200:
        print("TX success:", r.json())
    else:
        print("TX failed:", r.status_code, r.text)

def poll_rx():
    url = f"{BASE_URL}/rx"
    try:
        r = requests.get(url, timeout=1)
        if r.status_code == 200:
            data = r.json()
            if "packet" in data and data["packet"] is not False:
                print(f"RX packet ({datetime.datetime.now()}):")
                print(data["packet"])
                return data["packet"]
    except requests.exceptions.RequestException:
        pass


if __name__ == "__main__":
    print("Sending config...")
    send_config()

    # channels.json is a list of objects with the keys name and psk
    with open("channels.json") as f:
        channels_json = json.loads(f.read())

    meshtastic = meshtastic_dm.MeshtasticProto(lambda x: send_tx_packet(list(x)), channels_json)

    while True:
        for _ in range(30):
            rx = poll_rx()
            if rx:
                try:
                    meshtastic.packet_rx(bytes(rx["data"]), rx["rssi"], rx["snr"])
                except:
                    print("exception ingesting meshtastic packet")
                    traceback.print_exc()
            time.sleep(0.2)
