# Inspired from: https://gitlab.com/crankylinuxuser/meshtastic_sdr

import struct
import base64
import cryptography.hazmat.primitives.ciphers
import meshtastic
import json
import random

def meshtastic_channel_hash(channel_name: str, psk_b64: str) -> int:
    # https://github.com/meshtastic/firmware/blob/6f7149e9a2e54fcb85cfe14cfd2d1db1b25a05b0/src/mesh/Channels.cpp#L33-L50
    res = 0
    for b in (channel_name.encode("utf-8") + meshtastic_psk_to_key(psk_b64)):
        res ^= b
    return res

def meshtastic_psk_to_key(psk_b64: str) -> bytes:
    # https://github.com/meshtastic/firmware/blob/6f7149e9a2e54fcb85cfe14cfd2d1db1b25a05b0/src/mesh/Channels.cpp#L206-L254
    
    # https://github.com/meshtastic/firmware/blob/6f7149e9a2e54fcb85cfe14cfd2d1db1b25a05b0/src/mesh/Channels.h#L141-L143
    DEFAULTPSK = bytes([0xd4, 0xf1, 0xbb, 0x3a, 0x20, 0x29, 0x07, 0x59, 0xf0, 0xbc, 0xff, 0xab, 0xcf, 0x4e, 0x69, 0x01])
    psk = base64.b64decode(psk_b64)

    ret = psk

    if len(psk) == 0:
        raise Exception("""no PSK provided for a channel!
In the meshtastic firmware for the primary channel this means encryption off and for the secondary channels the firmware will use the primary channel key.
We don't do any of that. If you want to turn encryption off please provide a key with the value zero""")

    # single-byte keys are handled specially
    if len(psk) == 1:
        if psk[0] == 0:
            return b""  # Empty key -> no encryption
        else:
            ret = bytearray(DEFAULTPSK)
            ret[-1] += psk[0] - 1
    # pad short keys
    elif len(psk) < 16:
        print("WARNING: zero-padding short AES128 key")
        ret = bytes([0]*(16-len(psk))) + psk
    elif len(psk) < 32 and len(psk) != 16:
        print("WARNING: zero-padding short AES256 key")
        ret = bytes([0]*(32-len(psk))) + psk

    return ret

def meshtastic_parse_packet(data: bytes):
    # https://meshtastic.org/docs/overview/mesh-algo/
    HEADER_STRUCT = "<IIIBBBB"
    dest, sender, pid, flags, chsh, nxhop, rlnode = struct.unpack_from(HEADER_STRUCT, data)
    payload = data[struct.calcsize(HEADER_STRUCT):]
    return {
        "destination": dest,
        "sender": sender,
        "packetID": pid,
        "hopLimit": flags & 0x7,
        "wantAck": bool((flags >> 3) & 0x1),
        "viaMQTT": bool((flags >> 4) & 0x1),
        "hopStart": (flags >> 5) & 0x7,
        "channelHash": chsh,
        "nextHop": nxhop,
        "relayNode": rlnode,
        "payload": payload,
    }

def meshtastic_serialize_packet(pkt: dict) -> bytes:
    # https://meshtastic.org/docs/overview/mesh-algo/
    HEADER_STRUCT = "<IIIBBBB"

    flags = (
        (pkt["hopLimit"] & 0x7) | 
        (int(pkt["wantAck"]) << 3) |
        (int(pkt["viaMQTT"]) << 4) |
        ((pkt["hopStart"] & 0x7) << 5)
    )

    header = struct.pack(
        HEADER_STRUCT,
        pkt["destination"],
        pkt["sender"],
        pkt["packetID"],
        flags,
        pkt["channelHash"],
        pkt["nextHop"],
        pkt["relayNode"]
    )

    return header + pkt["payload"]

def meshtastic_decrypt(psk_b64: str, parsed_data: dict):
    key = meshtastic_psk_to_key(psk_b64)

    if len(key) == 0: # encryption disabled
        return parsed_data["payload"]

    # the nonce is the packet ID, zeros, then the sender node ID and then zeros again
    nonce = (
        parsed_data["packetID"] | (parsed_data["sender"] << 64)
    ).to_bytes(16, "little")

    cipher = cryptography.hazmat.primitives.ciphers.Cipher(
        cryptography.hazmat.primitives.ciphers.algorithms.AES(key),
        cryptography.hazmat.primitives.ciphers.modes.CTR(nonce),
    )
    decryptor = cipher.decryptor()

    decrypted = decryptor.update(parsed_data["payload"]) + decryptor.finalize()

    return decrypted

def meshtastic_encrypt(psk_b64: str, plaintext: bytes, packet_data: dict) -> bytes:
    key = meshtastic_psk_to_key(psk_b64)

    if len(key) == 0: # encryption disabled
        return plaintext

    # the nonce is the packet ID, zeros, then the sender node ID and then zeros again
    nonce = (
        packet_data["packetID"] | (packet_data["sender"] << 64)
    ).to_bytes(16, "little")

    cipher = cryptography.hazmat.primitives.ciphers.Cipher(
        cryptography.hazmat.primitives.ciphers.algorithms.AES(key),
        cryptography.hazmat.primitives.ciphers.modes.CTR(nonce),
    )
    encryptor = cipher.encryptor()

    encrypted = encryptor.update(plaintext) + encryptor.finalize()
    return encrypted

heard_packet_ids = set()

def meshtastic_decode(data_raw: bytes, rssi: int, snr: int):
    data = meshtastic.mesh_pb2.Data()
    try:
        data.ParseFromString(data_raw)
    except:
        print("invalid protobuf data")
        return
    print(data)
    #print(base64.b64encode(data.payload))

    # ping reply?
    if data.portnum == 1 and data.payload.decode("utf-8", errors="ignore").startswith("ping"):
        msg = meshtastic.mesh_pb2.Data()
        msg.portnum = 1
        msg.payload = f"pong rssi: {rssi}dBm SNR: {snr}dB\n{data.payload.decode('utf-8', errors='ignore')}".encode("utf-8")
        msg.bitfield = 0
        pkdata = {
            "destination": 0xFFFFFFFF,
            "sender": 0xAABBCCDD,
            "packetID": int.from_bytes(random.randbytes(4), "little"),
            "hopLimit": 3,
            "wantAck": False,
            "viaMQTT": False,
            "hopStart": 3,
            "channelHash": 9,
            "nextHop": 0,
            "relayNode": 0,
        }
        # make sure we don't relay our own packet again lmao
        heard_packet_ids.add(pkdata["packetID"])
        pkdata["payload"] = meshtastic_encrypt(channel_hash_map[242]["psk"], msg.SerializeToString(), pkdata)
        lora_send(meshtastic_serialize_packet(pkdata))

# channels.json is a list of objects with the keys name and psk
with open("channels.json") as f:
    channels_json = json.loads(f.read())

channel_hash_map = {meshtastic_channel_hash(c["name"], c["psk"]): c for c in channels_json}

def meshtastic_ingest_packet(data: bytes, rssi: int, snr: int):
    parsed = meshtastic_parse_packet(data)

    # relay?
    if parsed["hopLimit"] > 0 and parsed["packetID"] not in heard_packet_ids:
        print("relaying packet", parsed)
        pkdata = dict(parsed)
        pkdata["hopLimit"] -= 1
        lora_send(meshtastic_serialize_packet(pkdata))
    
    packet_heard_before = parsed["packetID"] in heard_packet_ids

    heard_packet_ids.add(parsed["packetID"])

    channel = channel_hash_map.get(parsed["channelHash"])
    if not channel:
        print("could not find channel for packet:", parsed)
        return
    print(f"received packet on channel '{channel['name']}':", parsed)
    data = meshtastic_decrypt(channel["psk"], parsed)
    if packet_heard_before:
        print("we heard this packet before. Not decoding again!")
        return
    meshtastic_decode(data, rssi, snr)

def lora_send(data: bytes):
    print("dummy lora send", data)
