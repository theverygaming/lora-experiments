from typing import Annotated
import fastapi
import sillyorm
from ... import orm
from .router import router
from .. import models


@router.get("/nodes")
async def node_list(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)]) -> list[models.node.MeshcoreNodePydanticWithId]:
    nodes = env["meshcore_node"].search([])
    return [models.node.MeshcoreNodePydanticWithId.from_record(record) for record in nodes]


@router.post("/nodes")
async def node_create(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], node: models.node.MeshcoreNodeEditPydantic) -> int:
    node = env["meshcore_node"].create(node.get_vals())
    return node.id


@router.get("/nodes/{node_id}")
async def node_get(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], node_id: int):
    node = env["meshcore_node"].browse(node_id)
    return models.node.MeshcoreNodePydanticWithId.from_record(node)


@router.put("/nodes/{node_id}")
async def node_update(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], node_id: int, node: models.node.MeshcoreNodeEditPydantic):
    env["meshcore_node"].browse(node_id).write(node.get_vals())


@router.delete("/nodes/{node_id}")
async def node_delete(env: Annotated[sillyorm.Environment, fastapi.Depends(orm.env)], node_id: int):
    env["meshcore_node"].browse(node_id).delete()
