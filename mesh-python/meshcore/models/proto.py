import logging
import time
import pydantic
import queue
import sillyorm
from ... import orm
from .. import meshcore


_logger = logging.getLogger(__name__)


@orm.register_model
class ProtoMeshcore(sillyorm.model.Model):
    _name = "proto_meshcore"
    _inherits = ["proto_common"]

    channels = sillyorm.fields.Many2many("meshcore_channel")

    lora_frequency = sillyorm.fields.Integer(required=True)
    lora_spreading_factor = sillyorm.fields.Integer(required=True)
    lora_bandwidth = sillyorm.fields.Integer(required=True)
    lora_coding_rate = sillyorm.fields.Integer(required=True)

    @sillyorm.model.constraints("lora_frequency", "lora_spreading_factor", "lora_bandwidth", "lora_coding_rate")
    def _check_lora(self):
        for record in self:
            if record.lora_frequency <= 0:
                raise Exception("invalid lora frequency")
            if record.lora_spreading_factor not in [5 + x for x in range(7)]:
                raise Exception("invalid lora spreading factor")
            if record.lora_bandwidth <= 0 or record.lora_bandwidth > 500000:
                raise Exception("invalid lora bandwidth")
            if record.lora_coding_rate < 5 or record.lora_coding_rate > 8:
                raise Exception("invalid lora coding rate")

    def _run(self, should_run_fn, data):
        if "proto" not in data:
            data["queue"] = queue.SimpleQueue()
            modem = self.modem_id.get_instance()
            modem.set_frequency(self.lora_frequency)
            modem.set_spreading_factor(self.lora_spreading_factor)
            modem.set_bandwidth(self.lora_bandwidth)
            modem.set_coding_rate(self.lora_coding_rate)
            data["proto"] = meshcore.Meshcore(modem, meshcore.MeshcoreNode({}), data["queue"])
        data["proto"].node.channels = {x.id: x.key for x in (self.channels if self.channels is not None else [])}
        data["proto"].start()
        while should_run_fn():
            if data["queue"].empty():
                time.sleep(0.1)
                continue
            lora_packet, packet, heard = data["queue"].get()
            if heard:
                continue
            try:
                # we need to create a new env, as we want to ensure things will be committed
                with orm.env_ctx() as env:
                    env["meshcore_packet"].from_meshcore_packet(self.id, packet, lora_packet.snr, lora_packet.rssi)
            except:
                _logger.exception("error creating meshcore_packet")
        data["proto"].stop()
