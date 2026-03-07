from typing import Annotated, Any
import json
import datetime
import base64
import fastapi
import sillyorm
from ... import orm
from .router import router
from . import pydantic_models


@router.get("/packets")
async def packet_list(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], domain: str | None = None, limit: int = 100, offset: int = 0) -> list[pydantic_models.MeshcorePacketPydanticWithId]:
    if limit > 1000:
        raise Exception("you may request at most 1000 packets per request")
    fields = {
        "proto_id": (False, int),
        "snr": (False, float),
        "rssi": (False, int),
        "outgoing": (False, bool),
        "timestamp_received": (True, datetime.datetime.fromisoformat),
        "route_type": (False, str),
        "payload_type": (False, str),
    }
    payload_defs = {
        "raw": (
            {
                "data": (True, base64.b64decode),
            },
            "meshcore_payload_raw",
            "payload_raw_id",
        ),
        "group_text": (
            {
                "channel_id": (False, int),
                "timestamp": (True, datetime.datetime.fromisoformat),
                "sender_name": (False, str),
                "message": (False, str),
            },
            "meshcore_payload_group_text",
            "payload_group_text_id",
        ),
        "advert": (
            {
                "node_type": (False, str),
                "pubkey": (True, base64.b64decode),
                "lat": (False, float),
                "lon": (False, float),
                "name": (False, str),
                "node_id": (False, int),
            },
            "meshcore_payload_advert",
            "payload_advert_id",
        ),
    }

    def check_search_part(part):
        exc_invalid = Exception(f"invalid search apart '{part}'")
        if isinstance(part, list):
            if len(part) != 3:
                raise exc_invalid
            if not isinstance(part[0], str) or not isinstance(part[1], str):
                raise exc_invalid
            if part[1] == "in" and not isinstance(part[2], list):
                raise exc_invalid
        elif isinstance(part, str):
            if part not in [
                "(",
                ")",
                "&",
                "!",
                "|",
            ]:
                raise exc_invalid
        else:
            raise exc_invalid

    def transform_search_part(part, fields):
        if part[0] not in fields:
            raise Exception(f"field {part[0]} not found")
        def tfix(x):
            isfn, t = fields[part[0]]
            if isfn:
                return t(x)
            else:
                if not isinstance(x, t):
                    raise Exception(f"invalid type for field {part[0]}")
            return x
        if part[1] == "in":
            part[2] = [tfix(x) for x in part[2]]
        else:
            part[2] = tfix(part[2])
        return tuple(part)

    domain_l = json.loads(domain) if domain is not None else []
    for i, part in enumerate(domain_l):
        check_search_part(part)
        if not isinstance(part, list):
            continue
        if part[0] in fields:
            domain_l[i] = transform_search_part(part, fields)
        elif part[0].startswith("payload_"):
            payload_type, field_name = part[0].split("_", maxsplit=1)[1].split(".", maxsplit=1)
            part[0] = field_name
            payload_fields, payload_model, payload_field = payload_defs[payload_type]
            domain_l[i] = (payload_field, "in", env[payload_model].search([transform_search_part(part, payload_fields)]).ids)

    packets = env["meshcore_packet"].search(domain_l, limit=limit, offset=offset)
    return [pydantic_models.MeshcorePacketPydanticWithId.from_record(record) for record in packets]


@router.get("/packets/{packet_id}")
async def packet_get(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], packet_id: int):
    packet = env["meshcore_packet"].browse(packet_id)
    return pydantic_models.MeshcorePacketPydanticWithId.from_record(packet)
