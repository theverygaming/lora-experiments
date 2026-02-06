import logging
import lora_modem
import struct
import enum
import dataclasses
from typing import Self
import datetime
import cryptography.hazmat.primitives.ciphers
import cryptography.hazmat.primitives.hashes
import cryptography.hazmat.primitives.hmac
import cryptography.hazmat.primitives.constant_time
import cryptography.hazmat.primitives.asymmetric.ed25519

_logger = logging.getLogger(__name__)

MAX_PATH_SIZE = 64
MAX_PACKET_PAYLOAD = 184

class RouteType(enum.Enum):
    TRANSPORT_FLOOD = 0x0
    FLOOD = 0x1
    DIRECT = 0x2
    TRANSPORT_DIRECT = 0x3

class PayloadType(enum.Enum):
    REQ = 0x0
    RESPONSE = 0x1
    TXT_MSG = 0x2
    ACK = 0x3
    ADVERT = 0x4
    GRP_TXT = 0x5
    GRP_DATA = 0x6
    ANON_REQ = 0x7
    PATH = 0x8
    TRACE = 0x9
    MULTIPART = 0xA
    CONTROL = 0xB
    RESERVED = 0xC # 0xC, 0xD and 0xE all map to this payload type so it can be compared easily 
    RAW_CUSTOM = 0xF

    def __call__(cls, value):
        # unknown reserved value -> map to 0xC
        if value >= 0xC and value <= 0xE:
            value = 0xC
        return super().__call__(cls, value)

class PayloadVersion(enum.Enum):
    V0 = 0x0
    FUTURE_V1 = 0x1 
    FUTURE_V2 = 0x2
    FUTURE_v3 = 0x3

class AdvertNodeType(enum.Enum):
    CHAT_NODE = 0x1
    REPEATER = 0x2
    ROOM_SERVER = 0x3
    SENSOR = 0x4

class Payload:
    @classmethod
    def deserialize(cls, data: bytes) -> Self:
        raise NotImplementedError()

    def serialize(self) -> bytes:
        raise NotImplementedError()

@dataclasses.dataclass
class PayloadRaw(Payload):
    data: bytes

    @classmethod
    def deserialize(cls, data: bytes) -> Self:
        return cls(data)

    def serialize(self) -> bytes:
        return self.data


@dataclasses.dataclass
class PayloadGroupText(Payload):
    channel: str
    timestamp: datetime.datetime
    sender_name: str
    message: str

    @classmethod
    def deserialize(cls, data: bytes) -> Self:
        channel_hash = int(data[0])
        cipher_mac = data[1:3]
        ciphertext = data[3:]

        _logger.debug("channel_hash: %s, cipher_mac: %s, ciphertext: %s", channel_hash, cipher_mac, ciphertext)

        CHANNELS = {
            "Public": bytes.fromhex("8b3387e9c5cdea6ac9e5edbaa115cd72"),
        }

        for name, key in CHANNELS.items():
            if len(key) != 16:
                raise Exception(f"channel key is {len(key)} bytes - not 16 bytes")
            sha256hash = cryptography.hazmat.primitives.hashes.Hash(cryptography.hazmat.primitives.hashes.SHA256())
            sha256hash.update(key)
            sha256_key = sha256hash.finalize()
            if sha256_key[0] == channel_hash:
                _logger.debug("found channel with matching hash")
                hmac = cryptography.hazmat.primitives.hmac.HMAC(key, cryptography.hazmat.primitives.hashes.SHA256())
                hmac.update(ciphertext)
                calculated_mac = hmac.finalize()[:2]

                if not cryptography.hazmat.primitives.constant_time.bytes_eq(calculated_mac, cipher_mac):
                    _logger.debug("mac mismatch calculated: %s got: %s", calculated_mac, cipher_mac)
                    continue

                cipher = cryptography.hazmat.primitives.ciphers.Cipher(
                    cryptography.hazmat.primitives.ciphers.algorithms.AES(key),
                    cryptography.hazmat.primitives.ciphers.modes.ECB(),
                )

                decryptor = cipher.decryptor()
                decrypted = decryptor.update(ciphertext) + decryptor.finalize()

                timestamp, = struct.unpack_from("<I", decrypted[0:4])
                attempt_num = int(decrypted[4]) & 0x3
                txt_type = (int(decrypted[4]) >> 2) & 0x3F
                # stripping the trailing zeros, those are left in because AES runs in blocks or something idk
                full_msg = bytearray(decrypted[5:]).rstrip(b"\x00").decode("utf-8")

                full_msg_split = full_msg.split(": ", maxsplit=1)

                kwargs = {
                    "channel": name,
                    "timestamp": datetime.datetime.fromtimestamp(timestamp),
                    "sender_name": full_msg_split[0],
                    "message": full_msg_split[1],
                }
                return cls(**kwargs)

        raise Exception("could not decrypt")

@dataclasses.dataclass
class PayloadAdvert(Payload):
    pubkey: bytes
    timestamp: datetime.datetime
    lat_lon: tuple[float, float] | None
    node_type: AdvertNodeType
    name: str | None

    @classmethod
    def deserialize(cls, data: bytes) -> Self:
        def _verify_signature(data, pubkey, signature):
            data_nokey = bytearray(data)
            # signing happens without the pubkey present in the message
            # https://github.com/meshcore-dev/MeshCore/blob/10067ada182e8fccd61406bb6c2e036c33d92e09/src/Mesh.cpp#L420-L428
            data_nokey[32 + 4:32 + 4 + 64] = []
            public_key = cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PublicKey.from_public_bytes(pubkey)
            public_key.verify(signature, data_nokey)

        kwargs = {}
        byte_idx = 0

        kwargs["pubkey"] = data[byte_idx:byte_idx+32]
        byte_idx += 32

        kwargs["timestamp"] = datetime.datetime.fromtimestamp(struct.unpack_from("<I", data[byte_idx:byte_idx+4])[0])
        byte_idx += 4

        signature = data[byte_idx:byte_idx+64]
        byte_idx += 64

        flags = data[byte_idx]
        byte_idx += 1

        # lower nibble of flags -> node type (0-15)
        # https://github.com/meshcore-dev/MeshCore/blob/10067ada182e8fccd61406bb6c2e036c33d92e09/src/helpers/AdvertDataHelpers.h#L7-L12
        kwargs["node_type"] = AdvertNodeType(flags & 0xF)

        # https://github.com/meshcore-dev/MeshCore/blob/10067ada182e8fccd61406bb6c2e036c33d92e09/src/helpers/AdvertDataHelpers.h#L14-L17
        LATLON_MASK = 0x10
        FEAT1_MASK = 0x20
        FEAT2_MASK = 0x40
        NAME_MASK = 0x80

        if (flags & LATLON_MASK) != 0:
            lat = struct.unpack_from("<I", data[byte_idx:byte_idx+4])[0]
            byte_idx += 4
            lon = struct.unpack_from("<I", data[byte_idx:byte_idx+4])[0]
            byte_idx += 4
            kwargs["lat_lon"] = (lat / 1000000, lon / 1000000)
        else:
            kwargs["lat_lon"] = None

        if (flags & FEAT1_MASK) != 0:
            byte_idx += 2
        
        if (flags & FEAT2_MASK) != 0:
            byte_idx += 2
        
        if (flags & NAME_MASK) != 0:
            kwargs["name"] = data[byte_idx:].decode("utf-8")
        else:
            kwargs["name"] = None
        
        _verify_signature(data, kwargs["pubkey"], signature)

        return cls(**kwargs)


@dataclasses.dataclass
class MeshcorePacket:
    route_type: RouteType
    payload_type: PayloadType
    payload_version: PayloadVersion
    transport_codes: list[int] | None
    path_len: int
    path: list[int]
    payload: Payload

    @classmethod
    def deserialize(cls, data: bytes) -> Self:
        # https://github.com/meshcore-dev/MeshCore/blob/6b52fb32301c273fc78d96183501eb23ad33c5bb/docs/packet_structure.md
        kwargs = {}

        byte_idx = 0

        # header field
        kwargs["route_type"] = RouteType(int(data[byte_idx]) & 0x3)
        kwargs["payload_type"] = PayloadType((int(data[byte_idx]) >> 2) & 0xF)
        kwargs["payload_version"] = PayloadVersion((int(data[byte_idx]) >> 6) & 0x3)
        if kwargs["payload_version"] != PayloadVersion.V0:
            raise Exception("unsupported payload version")
        byte_idx += 1

        # transport codes
        kwargs["transport_codes"] = None
        if kwargs["route_type"] in [RouteType.TRANSPORT_FLOOD, RouteType.TRANSPORT_DIRECT]:
            t1, t2 = struct.unpack_from("<HH", data[byte_idx:byte_idx+4])
            kwargs["transport_codes"] = [t1, t2]
            byte_idx += 4

        # path len
        kwargs["path_len"] = int(data[byte_idx])
        byte_idx += 1

        # path
        if kwargs["path_len"] > MAX_PATH_SIZE:
            raise Exception("MAX_PATH_SIZE exceeded")
        kwargs["path"] = []
        for _ in range(kwargs["path_len"]):
            kwargs["path"].append(int(data[byte_idx]))
            byte_idx += 1

        payload_bytes = data[byte_idx:]
        if len(payload_bytes) > MAX_PACKET_PAYLOAD:
            raise Exception("MAX_PACKET_PAYLOAD exceeded")
        
        PAYLOAD_CLASS_LOOKUP = {
            PayloadType.ADVERT: PayloadAdvert,
            PayloadType.GRP_TXT: PayloadGroupText,
        }

        try:
            kwargs["payload"] = PAYLOAD_CLASS_LOOKUP.get(kwargs["payload_type"], PayloadRaw).deserialize(payload_bytes)
        except:
            _logger.exception("error deserializing")
            kwargs["payload"] = PayloadRaw.deserialize(payload_bytes)

        return cls(**kwargs)

class Meshcore:
    def __init__(self, modem: lora_modem.LoraModem):
        self._modem = modem

    def start(self):
        def rx_cb(p):
            _logger.debug("deserialized: %s", MeshcorePacket.deserialize(p.data))
            # repeat packets that come from closeby nodes with high TX power, everything else with low TX power (rooftop repeater sorta deal)
            repeat_full_pwr = p.rssi > -80
            try:
                if repeat_full_pwr:
                    _logger.debug("repeating this packet with full power")
                    self._modem.set_tx_power(20)
                self._modem.tx(p)
            finally:
                if repeat_full_pwr:
                    self._modem.set_tx_power(0)
        self._modem.start(rx_cb)
        # EU/UK (Narrow) preset
        self._modem.set_gain(0) # AGC
        self._modem.set_frequency(869618000)
        self._modem.set_spreading_factor(8)
        self._modem.set_bandwidth(62500)
        self._modem.set_coding_rate(8)
        self._modem.set_preamble_length(16)
        self._modem.set_syncword(0x12) # Meshcore (RADIOLIB_SX126X_SYNC_WORD_PRIVATE)
        self._modem.set_tx_power(0) # don't wanna annoy anyone with my silly packets rn # TODO: more power when this works properly
        self._modem.set_aux_lora_settings(
            crc=True,
            invert_iq=False,
            low_data_rate_optimize=False,
        )

    def stop(self):
        self._modem.stop()
