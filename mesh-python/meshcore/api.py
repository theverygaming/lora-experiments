from typing import Annotated
import logging
import time
import datetime
import asyncio
import base64
import fastapi
import pydantic
import queue
import sillyorm
from .. import orm
from . import meshcore
from . import models


_logger = logging.getLogger(__name__)
router = fastapi.APIRouter()


def startup():
    with orm.env_ctx() as env:
        for p in env["proto_meshcore"].search([("enabled", "=", True)]):
            p.start()
