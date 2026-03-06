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
