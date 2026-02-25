import logging
import datetime
import pydantic
import queue
import sillyorm
from ... import orm
from .. import meshcore

_logger = logging.getLogger(__name__)


@orm.register_model
class MeshcorePayload(sillyorm.model.AbstractModel):
    _name = "meshcore_payload"

    packet_id = sillyorm.fields.Many2one("meshcore_packet", required=True)

    def from_meshcore_payload(self, packet, payload: meshcore.Payload):
        raise NotImplementedError()


@orm.register_model
class MeshcorePayloadRaw(sillyorm.model.Model):
    _name = "meshcore_payload_raw"
    _inherits = ["meshcore_payload"]

    data = sillyorm.fields.LargeBinary(required=True)

    def from_meshcore_payload(self, packet, payload: meshcore.Payload):
        return self.create({
            "packet_id": packet.id,
            "data": payload.data,
        })


@orm.register_model
class MeshcorePayloadGroupText(sillyorm.model.Model):
    _name = "meshcore_payload_group_text"
    _inherits = ["meshcore_payload"]

    channel = sillyorm.fields.Many2one("meshcore_channel", required=True)
    timestamp = sillyorm.fields.Datetime(tzinfo=datetime.timezone.utc, convert_tz=True, required=True)
    sender_name = sillyorm.fields.String(required=True)
    message = sillyorm.fields.String(required=True)

    def from_meshcore_payload(self, packet, payload: meshcore.Payload):
        return self.create({
            "packet_id": packet.id,
            "channel": payload.channel_key,
            "timestamp": payload.timestamp,
            "sender_name": payload.sender_name,
            "message": payload.message,
        })


@orm.register_model
class MeshcorePayloadAdvert(sillyorm.model.Model):
    _name = "meshcore_payload_advert"
    _inherits = ["meshcore_payload"]

    node_type = sillyorm.fields.Selection(["companion", "repeater", "roomserver", "sensor"], required=True)
    pubkey = sillyorm.fields.LargeBinary(required=True)
    lat = sillyorm.fields.Float()
    lon = sillyorm.fields.Float()
    name = sillyorm.fields.String()

    node_id = sillyorm.fields.Many2one("meshcore_node", required=True)

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

    def from_meshcore_payload(self, packet, payload: meshcore.Payload):
        create_data = {
            "packet_id": packet.id,
            "pubkey": payload.pubkey,
            "node_type": {
                meshcore.AdvertNodeType.CHAT_NODE: "companion",
                meshcore.AdvertNodeType.REPEATER: "repeater",
                meshcore.AdvertNodeType.ROOM_SERVER: "roomserver",
                meshcore.AdvertNodeType.SENSOR: "sensor",
            }[payload.node_type],
        }
        if payload.name is not None:
            create_data["name"] = payload.name
        if payload.lat_lon is not None:
            create_data["lat"], create_data["lon"] = payload.lat_lon

        create_data["node_id"] = self.env["meshcore_node"].from_advert_payload_vals(create_data).id

        return self.create(create_data)
