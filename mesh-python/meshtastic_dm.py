# Inspired from: https://gitlab.com/crankylinuxuser/meshtastic_sdr

import logging
import struct
import base64
import cryptography.hazmat.primitives.ciphers
import meshtastic
import json
import random
import uuid
import google.protobuf.json_format
import lora_modem


_logger = logging.getLogger(__name__)


class Meshtastic:
    def __init__(self, modem: lora_modem.LoraModem, channels: list[dict]):
        self._modem = modem

        self._channels = {
            c["name"]: {
                "hash": self._channel_hash(c2 := c | {
                    "key": self._psk_to_key(c["psk"]),
                })
            } | c2
            for c in channels
        }

        self._channel_hash_map = {c["hash"]: c for c in self._channels.values()}
        self._heard_packet_ids = set()

        self._node_id = int.from_bytes(random.Random(uuid.getnode()).randbytes(4), "little")
        _logger.info("chose random node ID: %d (0x%x)", self._node_id, self._node_id)

    def start(self):
        def rx_cb(p):
            try:
                self.packet_rx(p.data, p.rssi, p.snr)
            except:
                _logger.exception("exception ingesting meshtastic packet")
        self._modem.start(rx_cb)
        # LongFast EU_868
        self._modem.set_gain(0) # AGC
        self._modem.set_frequency(869525000)
        self._modem.set_spreading_factor(11)
        self._modem.set_bandwidth(250000)
        self._modem.set_coding_rate(5)
        self._modem.set_preamble_length(16)
        self._modem.set_syncword(0x2b) # meshtastic
        self._modem.set_tx_power(20)
        self._modem.set_aux_lora_settings(
            crc=True,
            invert_iq=False,
            low_data_rate_optimize=False,
        )

    def stop(self):
        self._modem.stop()

    def packet_rx(self, data: bytes, rssi: int, snr: float):
        packet = self.packet_deserialize(data, {
            "rssi": rssi,
            "snr": snr,
        })

        _logger.debug("received packet on channel '%s': %s", self._channel_hash_map.get(packet["channelHash"], {}).get("name"), repr(packet))

        if "payload" in packet:
            protobuf_dict = google.protobuf.json_format.MessageToDict(packet["payload"], preserving_proto_field_name=True)
            protobuf_dict_payload_bytes = base64.b64decode(protobuf_dict.get("payload", ""))
            match protobuf_dict["portnum"]:
                case "TEXT_MESSAGE_APP":
                    protobuf_dict["payload"] = protobuf_dict_payload_bytes.decode("utf-8")
            pb_lookup = {
                "POSITION_APP": meshtastic.mesh_pb2.Position,
                "NODEINFO_APP": meshtastic.mesh_pb2.NodeInfo,
                "ROUTING_APP": meshtastic.mesh_pb2.Routing,
                "TEXT_MESSAGE_COMPRESSED_APP": meshtastic.mesh_pb2.Compressed,
                "WAYPOINT_APP": meshtastic.mesh_pb2.Waypoint,
                "TELEMETRY_APP": meshtastic.telemetry_pb2.Telemetry,
                "TRACEROUTE_APP": meshtastic.mesh_pb2.RouteDiscovery,
                "NEIGHBORINFO_APP": meshtastic.mesh_pb2.NeighborInfo,
            }
            if protobuf_dict["portnum"] in pb_lookup:
                pbd = pb_lookup[protobuf_dict["portnum"]]()
                pbd.ParseFromString(protobuf_dict_payload_bytes)
                protobuf_dict["payload"] = google.protobuf.json_format.MessageToDict(pbd, preserving_proto_field_name=True)

            _logger.debug("packet decoded protobuf: %s", protobuf_dict)

        # relay?
        if packet["hopLimit"] > 0 and packet["packetID"] not in self._heard_packet_ids and packet["destination"] != self._node_id:
            # TODO: meshtastic actually has intelligent algos for this, if
            # this code was deployed on every node the network would be ass lmao
            # _fix it_
            npkdata = dict(packet)
            npkdata["hopLimit"] -= 1
            _logger.debug("relaying packet: %s", npkdata["packetID"])
            self._heard_packet_ids.add(packet["packetID"])
            # traceroute to someone else?
            if "payload" in packet and protobuf_dict["portnum"] == "TRACEROUTE_APP":
                _logger.debug("processing traceroute")
                # FIXME: traceroute seems to use nextHop on the way back.. we just ignore that lmfao.. we should probably not (https://github.com/meshtastic/firmware/blob/57a3ff8dfcc7b2b4f766de224cc80376e7332564/src/modules/TraceRouteModule.cpp#L269)
                new_pb_payload = protobuf_dict["payload"]

                # figure out direction and which values to set
                is_on_way_back = "request_id" in protobuf_dict
                hops_away = packet["hopStart"] - packet["hopLimit"]
                route_key = "route" if not is_on_way_back else "route_back"
                snr_key = "snr_towards" if not is_on_way_back else "snr_back"
                # ensure snr and route arrays exist
                for k in [route_key, snr_key]:
                    if k not in new_pb_payload:
                        new_pb_payload[k] = []

                # fix the route (there may have been unknown hops)
                if hops_away >= 0:
                    diff = hops_away - len(new_pb_payload[route_key])
                    for _ in range(diff):
                        new_pb_payload[route_key].append(0xFFFFFFFF) # broadcast = unknown node
                    diff = hops_away - len(new_pb_payload[snr_key])
                    for _ in range(diff):
                        new_pb_payload[snr_key].append(-128) # minimum value of 8-bit signed (two's complement) integer = unknown node
                
                # add the current hop to the route
                new_pb_payload[snr_key].append(int(snr * 4)) # SNR is converted to a byte by multiplying to by 4
                new_pb_payload[route_key].append(self._node_id)

                _logger.debug("processed traceroute: %s", new_pb_payload)

                npkdata["payload"].payload = google.protobuf.json_format.ParseDict(new_pb_payload, meshtastic.mesh_pb2.RouteDiscovery(), ignore_unknown_fields=False).SerializeToString()
            self._modem.tx(lora_modem.LoraPacket(self.packet_serialize(npkdata)))
        else:
            self._heard_packet_ids.add(packet["packetID"])

        if "payload" not in packet:
            _logger.debug("no payload in packet, cannot process further")
            return

        # TODO: traceroute to us?
        # if protobuf_dict["portnum"] == "TRACEROUTE_APP" and packet["destination"] == self._node_id:

        # ping reply?
        if packet["payload"].portnum == meshtastic.portnums_pb2.PortNum.TEXT_MESSAGE_APP and packet["channelHash"] == self._channels["gg"]["hash"] and packet["payload"].payload.decode("utf-8", errors="ignore").startswith("ping"):
            msg = meshtastic.mesh_pb2.Data()
            msg.portnum = meshtastic.portnums_pb2.PortNum.TEXT_MESSAGE_APP
            msg.payload = f"pong RSSI: {rssi}dBm SNR: {snr}dB".encode("utf-8")
            msg.bitfield = 0
            msg.reply_id = packet["packetID"]
            npkdata = {
                "destination": 0xFFFFFFFF,
                "sender": self._node_id,
                "packetID": int.from_bytes(random.randbytes(4), "little"),
                "hopLimit": 3,
                "wantAck": False,
                "viaMQTT": False,
                "hopStart": 3,
                "channelHash": self._channels["gg"]["hash"],
                "nextHop": 0,
                "relayNode": 0,
                "payload": msg,
            }
            # make sure we don't relay our own packet again lmao
            self._heard_packet_ids.add(npkdata["packetID"])

            self._modem.tx(lora_modem.LoraPacket(self.packet_serialize(npkdata)))

    def packet_serialize(self, packet: dict) -> bytes:
        def packet_encrypt(packet: dict):
            cipher = self._packet_prepare_cipher(packet)
            if not cipher:  # unencrypted
                return packet["payload_decrypted"]
            encryptor = cipher.encryptor()
            encrypted = encryptor.update(packet["payload_decrypted"]) + encryptor.finalize()
            return encrypted

        # if the packet has a payload, we must serialize it
        if "payload" in packet:
            packet["payload_decrypted"] = packet["payload"].SerializeToString()

        # if the packet has a decrypted payload we must encrypt it
        if "payload_decrypted" in packet:
            packet["payload_encrypted"] = packet_encrypt(packet)

        # https://meshtastic.org/docs/overview/mesh-algo/
        HEADER_STRUCT = "<IIIBBBB"

        flags = (
            (packet["hopLimit"] & 0x7) | 
            (int(packet["wantAck"]) << 3) |
            (int(packet["viaMQTT"]) << 4) |
            ((packet["hopStart"] & 0x7) << 5)
        )

        header = struct.pack(
            HEADER_STRUCT,
            packet["destination"],
            packet["sender"],
            packet["packetID"],
            flags,
            packet["channelHash"],
            packet["nextHop"],
            packet["relayNode"]
        )

        return header + packet["payload_encrypted"]

    def packet_deserialize(self, data: bytes, extra_data: dict) -> bytes:
        def packet_decrypt(packet: dict):
            cipher = self._packet_prepare_cipher(packet)
            if not cipher:  # unencrypted
                return packet["payload_encrypted"]
            decryptor = cipher.decryptor()
            decrypted = decryptor.update(packet["payload_encrypted"]) + decryptor.finalize()
            return decrypted

        # deserialize
        # https://meshtastic.org/docs/overview/mesh-algo/
        HEADER_STRUCT = "<IIIBBBB"
        dest, sender, pid, flags, chsh, nxhop, rlnode = struct.unpack_from(HEADER_STRUCT, data)
        payload = data[struct.calcsize(HEADER_STRUCT):]
        packet = {
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
            "payload_encrypted": payload,
        }

        packet = packet | extra_data

        try:
            payload_decrypted = packet_decrypt(packet)
            if payload_decrypted:
                packet["payload_decrypted"] = payload_decrypted
                pdata = meshtastic.mesh_pb2.Data()
                pdata.ParseFromString(packet["payload_decrypted"])
                packet["payload"] = pdata
            else:
                _logger.debug("could not decrypt packet:", packet)
        except:
            _logger.exception("exception decrypting packet")

        return packet

    def _packet_prepare_cipher(self, packet: dict):
        channel = self._channel_hash_map.get(packet["channelHash"])
        if not channel:
            raise Exception("no channel for cipher found")
        key = channel["key"]

        if len(key) == 0: # encryption disabled
            return None

        # the nonce is the packet ID, zeros, then the sender node ID and then zeros again
        nonce = (
            packet["packetID"] | (packet["sender"] << 64)
        ).to_bytes(16, "little")

        cipher = cryptography.hazmat.primitives.ciphers.Cipher(
            cryptography.hazmat.primitives.ciphers.algorithms.AES(key),
            cryptography.hazmat.primitives.ciphers.modes.CTR(nonce),
        )
        return cipher

    @staticmethod
    def _channel_hash(channel: dict) -> int:
        # https://github.com/meshtastic/firmware/blob/6f7149e9a2e54fcb85cfe14cfd2d1db1b25a05b0/src/mesh/Channels.cpp#L33-L50
        res = 0
        for b in (channel["name"].encode("utf-8") + channel["key"]):
            res ^= b
        return res

    @staticmethod
    def _psk_to_key(psk_b64: str) -> bytes:
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
            _logger.warning("zero-padding short AES128 key")
            ret = bytes([0]*(16-len(psk))) + psk
        elif len(psk) < 32 and len(psk) != 16:
            _logger.warning("zero-padding short AES256 key")
            ret = bytes([0]*(32-len(psk))) + psk

        return ret
