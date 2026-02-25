import logging
import datetime
import pydantic
import queue
import sillyorm
from ... import orm
from .. import meshcore

_logger = logging.getLogger(__name__)


@orm.register_model
class MeshcoreNode(sillyorm.model.Model):
    _name = "meshcore_node"

    node_type = sillyorm.fields.Selection(["companion", "repeater", "roomserver", "sensor"], required=True)
    pubkey = sillyorm.fields.LargeBinary(required=True, unique=True)
    last_heard = sillyorm.fields.Datetime(tzinfo=datetime.timezone.utc, convert_tz=True, required=True)
    lat = sillyorm.fields.Float()
    lon = sillyorm.fields.Float()
    name = sillyorm.fields.String()
    out_path = sillyorm.fields.JSON()

    advert_payload_ids = sillyorm.fields.One2many("meshcore_payload_advert", "node_id")

    @sillyorm.model.constraints("pubkey")
    def _check_pubkey(self):
        for record in self:
            if len(record.pubkey) != 32:
                raise Exception("pubkeys must always be 32 bytes")

    @sillyorm.model.constraints("lat", "lon")
    def _check_lat_lon(self):
        for record in self:
            if (record.lat is not None) != (record.lon is not None):
                raise Exception("lat and lon must always be set together")

    @sillyorm.model.constraints("out_path")
    def _check_path(self):
        for record in self:
            if record.out_path is None:
                continue
            if not isinstance(record.out_path, list):
                raise Exception("path must be list")
            for x in record.out_path:
                if not isinstance(x, int) or not (x >= 0 and x <= 255):
                    raise Exception("path item must be integer from 0-255")

    def from_advert_payload_vals(self, vals: dict):
        node_data = {
            "node_type": vals["node_type"],
            "last_heard": datetime.datetime.now(datetime.timezone.utc),
        }
        if vals.get("name") is not None:
            node_data["name"] = vals.get("name")
        if vals.get("lat") is not None and vals.get("lon") is not None:
            node_data["lat"] = vals.get("lat")
            node_data["lon"] = vals.get("lon")

        found = self.search([("pubkey", "=", vals["pubkey"])])
        if found:
            found.write(node_data)
            return found
        create_data = {
            "pubkey": vals["pubkey"],
            **node_data,
        }
        return self.create(create_data)
