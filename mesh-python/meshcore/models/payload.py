import logging
import datetime
import sillyorm
from ... import orm
from .. import meshcore

_logger = logging.getLogger(__name__)


@orm.register_model
class MeshcorePacket(sillyorm.model.Model):
    _name = "meshcore_packet"
    _extends = "meshcore_packet"

    payload_raw_id = sillyorm.fields.Many2one("meshcore_payload_raw")
    payload_group_text_id = sillyorm.fields.Many2one("meshcore_payload_group_text")
    payload_advert_id = sillyorm.fields.Many2one("meshcore_payload_advert")

    def _get_payload_field(self, payload):
        if isinstance(payload, meshcore.PayloadAdvert):
            return ("payload_advert_id", "meshcore_payload_advert")
        elif isinstance(payload, meshcore.PayloadGroupText):
            return ("payload_group_text_id", "meshcore_payload_group_text")
        elif isinstance(payload, meshcore.PayloadRaw):
            return ("payload_raw_id", "meshcore_payload_raw")
        return super()._get_payload_field(payload)


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

    channel_id = sillyorm.fields.Many2one("meshcore_channel", required=True)
    timestamp = sillyorm.fields.Datetime(tzinfo=datetime.timezone.utc, convert_tz=True, required=True)
    sender_name = sillyorm.fields.String(required=True)
    message = sillyorm.fields.String(required=True)

    def from_meshcore_payload(self, packet, payload: meshcore.Payload):
        return self.create({
            "packet_id": packet.id,
            "channel_id": payload.channel_key,
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

    # FIXME: this should be ondelete cascade but we got issues cuz of the references in
    # the base payload to packet_id which back-references the payload.
    # if we cascade this, meshcore_packet records will be left without any valid references..
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
