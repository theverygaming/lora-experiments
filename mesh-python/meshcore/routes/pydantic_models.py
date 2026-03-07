from typing import Literal
import base64
import datetime
import pydantic


class MeshcoreNodeEditPydantic(pydantic.BaseModel):
    node_type: Literal["companion", "repeater", "roomserver", "sensor"]
    pubkey: pydantic.Base64Bytes
    lat: float | None
    lon: float | None
    name: str | None
    out_path: list[int] | None

    def get_vals(self):
        d = self.model_dump()
        d["pubkey"] = self.pubkey
        return d


class MeshcoreNodePydantic(MeshcoreNodeEditPydantic):
    last_heard: datetime.datetime | None

    #TODO: advert_payload_ids:


class MeshcoreNodePydanticWithId(MeshcoreNodePydantic):
    id: int

    @staticmethod
    def from_record(record):
        return MeshcoreNodePydanticWithId(
            node_type=record.node_type,
            pubkey=base64.b64encode(record.pubkey),
            last_heard=record.last_heard,
            lat=record.lat,
            lon=record.lon,
            name=record.name,
            out_path=record.out_path,
            id=record.id,
        )


class MeshcoreChannelPydantic(pydantic.BaseModel):
    name: str
    key: pydantic.Base64Bytes


class MeshcoreChannelPydanticWithId(MeshcoreChannelPydantic):
    id: int


class MeshcorePayloadRawPydantic(pydantic.BaseModel):
    payload_type_decoded: Literal["raw"] = "raw"
    data: pydantic.Base64Bytes

    @staticmethod
    def from_record(record):
        return MeshcorePayloadRawPydantic(
            data=base64.b64encode(record.data),
        )


class MeshcorePayloadGroupTextPydantic(pydantic.BaseModel):
    payload_type_decoded: Literal["group_text"] = "group_text"
    channel_id: int
    timestamp: datetime.datetime
    sender_name: str
    message: str

    @staticmethod
    def from_record(record):
        return MeshcorePayloadGroupTextPydantic(
            channel_id=record.channel_id.id,
            timestamp=record.timestamp,
            sender_name=record.sender_name,
            message=record.message,
        )


class MeshcorePayloadAdvertPydantic(pydantic.BaseModel):
    payload_type_decoded: Literal["advert"] = "advert"
    node_type: Literal["companion", "repeater", "roomserver", "sensor"]
    pubkey: pydantic.Base64Bytes
    lat: float | None
    lon: float | None
    name: str | None
    node_id: int

    @staticmethod
    def from_record(record):
        return MeshcorePayloadAdvertPydantic(
            node_type=record.node_type,
            pubkey=base64.b64encode(record.pubkey),
            lat=record.lat,
            lon=record.lon,
            name=record.name,
            node_id=record.node_id.id,
        )


class MeshcorePacketPydantic(pydantic.BaseModel):
    proto_id: int
    snr: float | None
    rssi: int | None
    outgoing: bool
    timestamp_received: datetime.datetime
    route_type: Literal["flood", "direct", "transport_flood", "transport_direct"]
    payload_type: Literal[
        "req",
        "response",
        "txt_msg",
        "ack",
        "advert",
        "grp_txt",
        "grp_data",
        "anon_req",
        "path",
        "trace",
        "multipart",
        "control",
        "reserved_0xc",
        "reserved_0xd",
        "reserved_0xe",
        "raw_custom",
    ]
    transport_codes: list[int] | None
    path: list[int]
    payload: MeshcorePayloadRawPydantic | MeshcorePayloadGroupTextPydantic | MeshcorePayloadAdvertPydantic = pydantic.Field(discriminator="payload_type_decoded")


class MeshcorePacketPydanticWithId(MeshcorePacketPydantic):
    id: int

    @staticmethod
    def from_record(record):
        payload = record.get_payload()
        payload_pydantic = {
            "meshcore_payload_raw": MeshcorePayloadRawPydantic,
            "meshcore_payload_group_text": MeshcorePayloadGroupTextPydantic,
            "meshcore_payload_advert": MeshcorePayloadAdvertPydantic,
        }[payload._name].from_record(payload)
        return MeshcorePacketPydanticWithId(
            proto_id=record.proto_id.id,
            snr=record.snr,
            rssi=record.rssi,
            outgoing=record.outgoing,
            timestamp_received=record.timestamp_received,
            route_type=record.route_type,
            payload_type=record.payload_type,
            transport_codes=record.transport_codes,
            path=record.path,
            payload=payload_pydantic,
            id=record.id,
        )
