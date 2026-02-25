import logging
import datetime
import pydantic
import queue
import sillyorm
from ... import orm
from .. import meshcore

_logger = logging.getLogger(__name__)

@orm.register_model
class MeshcoreChannel(sillyorm.model.Model):
    _name = "meshcore_channel"

    name = sillyorm.fields.String(required=True)
    key = sillyorm.fields.LargeBinary(required=True)

    @sillyorm.model.constraints("key")
    def _check_key(self):
        for record in self:
            if len(record.key) != 16:
                raise Exception("keys must always be 16 bytes")
