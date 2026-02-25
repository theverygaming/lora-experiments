import logging
import datetime
import pydantic
import queue
import sillyorm
from ... import orm
from .. import meshcore


_logger = logging.getLogger(__name__)


@orm.register_model
class MeshcorePacket(sillyorm.model.Model):
    _name = "meshcore_packet"

    snr = sillyorm.fields.Float()
    rssi = sillyorm.fields.Integer()
    outgoing = sillyorm.fields.Boolean(required=True)

    timestamp_received = sillyorm.fields.Datetime(tzinfo=datetime.timezone.utc, convert_tz=True, required=True)

    route_type = sillyorm.fields.Selection(["flood", "direct", "transport_flood", "transport_direct"], required=True)
    payload_type = sillyorm.fields.Selection(
        [
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
        ],
        required=True,
    )
    transport_codes = sillyorm.fields.JSON()
    path = sillyorm.fields.JSON(required=True)

    @sillyorm.model.constraints("outgoing")
    def _check_outgoing(self):
        for record in self:
            has_snr = record.snr is not None
            has_rssi = record.rssi is not None
            if record.outgoing:
                if has_snr or has_rssi:
                    raise Exception("outgoing packets cannot have SNR or RSSI")
            else:
                if not has_snr or not has_rssi:
                    raise Exception("incoming packets must have SNR or RSSI")


    @sillyorm.model.constraints("transport_codes")
    def _check_transport_codes(self):
        for record in self:
            if record.transport_codes is None:
                continue
            if not isinstance(record.transport_codes, list):
                raise Exception("transport_codes must be list")
            for x in record.transport_codes:
                if not isinstance(x, int) or not (x >= 0 and x < 65535):
                    raise Exception("transport_codes item must be integer from 0-65535")

    @sillyorm.model.constraints("path")
    def _check_path(self):
        for record in self:
            if not isinstance(record.path, list):
                raise Exception("path must be list")
            for x in record.path:
                if not isinstance(x, int) or not (x >= 0 and x <= 255):
                    raise Exception("path item must be integer from 0-255")

    # link to payload
    # technically these should be required, but I sense a chicken-egg problem with the back link on the payload..
    payload_model = sillyorm.fields.String()
    payload_id = sillyorm.fields.Integer()

    @sillyorm.model.constraints("payload_model", "payload_id")
    def _payload_link_check(self):
        for record in self:
            if not (record.payload_model is None) == (record.payload_id is None):
                raise Exception("both payload_model and payload_id must be set at the same time")
            if record.payload_model is None:
                continue
            if record.env[record.payload_model].browse(record.payload_id) is None:
                raise Exception("linked payload record could not be found")

    def from_meshcore_packet(self, packet, snr: float | None, rssi: int | None):
        meshcore_packet = self.create({
            "snr": snr,
            "rssi": rssi,
            "outgoing": False,
            "timestamp_received": datetime.datetime.now(datetime.timezone.utc),
            "route_type": {
                meshcore.RouteType.TRANSPORT_FLOOD: "transport_flood",
                meshcore.RouteType.FLOOD: "flood",
                meshcore.RouteType.DIRECT: "direct",
                meshcore.RouteType.TRANSPORT_DIRECT: "transport_direct",
            }[packet.route_type],
            "payload_type": {
                meshcore.PayloadType.REQ: "req",
                meshcore.PayloadType.RESPONSE: "response",
                meshcore.PayloadType.TXT_MSG: "txt_msg",
                meshcore.PayloadType.ACK: "ack",
                meshcore.PayloadType.ADVERT: "advert",
                meshcore.PayloadType.GRP_TXT: "grp_txt",
                meshcore.PayloadType.GRP_DATA: "grp_data",
                meshcore.PayloadType.ANON_REQ: "anon_req",
                meshcore.PayloadType.PATH: "path",
                meshcore.PayloadType.TRACE: "trace",
                meshcore.PayloadType.MULTIPART: "multipart",
                meshcore.PayloadType.CONTROL: "control",
                meshcore.PayloadType.RESERVED_0XC: "reserved_0xc",
                meshcore.PayloadType.RESERVED_0XD: "reserved_0xd",
                meshcore.PayloadType.RESERVED_0XE: "reserved_0xe",
                meshcore.PayloadType.RAW_CUSTOM: "raw_custom",
            }[packet.payload_type],
            "transport_codes": packet.transport_codes,
            "path": packet.path,
        })
        if isinstance(packet.payload, meshcore.PayloadAdvert):
            payload_model = "meshcore_payload_advert"
        elif isinstance(packet.payload, meshcore.PayloadGroupText):
            payload_model = "meshcore_payload_group_text"
        elif isinstance(packet.payload, meshcore.PayloadRaw):
            payload_model = "meshcore_payload_raw"
        else:
            raise Exception(f"unknown payload {packet.payload}")
        payload = self.env[payload_model].from_meshcore_payload(meshcore_packet, packet.payload)
        meshcore_packet.write({
            "payload_model": payload._name,
            "payload_id": payload.id,
        })
        return meshcore_packet
