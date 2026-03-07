from typing import Annotated
import base64
import fastapi
import sillyorm
from ... import orm
from .router import router
from . import pydantic_models


@router.get("/channels")
async def channel_list(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)]) -> list[pydantic_models.MeshcoreChannelPydanticWithId]:
    channels = env["meshcore_channel"].search([])
    return [pydantic_models.MeshcoreChannelPydanticWithId(name=c.name, key=base64.b64encode(c.key), id=c.id) for c in channels]


@router.post("/channels")
async def channel_create(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], channel: pydantic_models.MeshcoreChannelPydantic) -> int:
    channel_id = env["meshcore_channel"].create({"name": channel.name, "key": channel.key}).id
    return channel_id


@router.get("/channels/{channel_id}")
async def channel_get(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], channel_id: int):
    channel = env["meshcore_channel"].browse(channel_id)
    return pydantic_models.MeshcoreChannelPydantic(name=channel.name, key=base64.b64encode(channel.key))


@router.put("/channels/{channel_id}")
async def channel_update(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], channel_id: int, channel: pydantic_models.MeshcoreChannelPydantic):
    env["meshcore_channel"].browse(channel_id).write({
        "name": channel.name,
        "key": channel.key,
    })


@router.delete("/channels/{channel_id}")
async def channel_delete(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], channel_id: int):
    env["meshcore_channel"].browse(channel_id).delete()
