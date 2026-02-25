from typing import Annotated
import logging
import threading
import contextlib
import fastapi
import pydantic
import sillyorm
from . import orm
from .meshcore import api as meshcore_api
from . import esplora

_active_protos = {}

@orm.register_model
class ProtoCommon(sillyorm.model.AbstractModel):
    _name = "proto_common"

    name = sillyorm.fields.String(required=True)
    enabled = sillyorm.fields.Boolean(required=True, default=False)

    modem_id = sillyorm.fields.Many2one("lora_modem")

    def create(self, vals):
        mid = None
        if "modem_id" in vals and vals["modem_id"] is not None:
            mid = vals["modem_id"]
            del vals["modem_id"]
        created = super().create(vals)
        if mid is not None:
            created.env["lora_modem"].browse(mid).proto_link(created)
        if created.enabled:
            created.start()
        return created

    def write(self, vals):
        if "modem_id" in vals and not (getattr(self.env, "_common_proto_write_modem_id_ignore", False)):
            mid = vals["modem_id"]
            del vals["modem_id"]
            for record in self:
                # unset
                if mid is None and record.modem_id is not None:
                    record.modem_id.proto_unlink()
                    continue
                # set
                if mid is not None:
                    # nothing..
                    if mid == record.modem_id:
                        continue
                    # replace
                    if record.modem_id is not None:
                        record.modem_id.proto_unlink()
                    record.env["lora_modem"].browse(mid).proto_link(record)
                    continue
                raise Exception("unreachable")
        super().write(vals)
        if "enabled" in vals:
            for record in self:
                if vals["enabled"]:
                    record.start()
                else:
                    record.stop()

    def delete(self):
        for record in self:
            record._active_rm()
            if record.modem_id is not None:
                record.modem_id.proto_unlink()
        return super().delete()

    def _active_rm(self):
        global _active_protos
        self.ensure_one()
        self.stop()
        id_ = str(self)
        if id_ in _active_protos:
            del _active_protos[id_]

    def _run(self, should_run_fn, data):
        raise NotImplementedError()

    def _start(self, data):
        """
        launch thread that runs the proto, takes runtime data dict, returns thread object
        """
        data["thread_stop"] = threading.Event()
        recmodel = self._name
        recid = self.id
        def _thread():
            with orm.env_ctx() as env:
                env[recmodel].browse(recid)._run(lambda: not data["thread_stop"].is_set(), data["user"])
        tobj = threading.Thread(target=_thread)
        tobj.start()
        return tobj

    @classmethod
    def _stop(cls, data, t):
        """
        kill thread that ran the proto, takes runtime data dict and thread object
        """
        data["thread_stop"].set()
        t.join()
        del data["thread_stop"]
    
    @classmethod
    def stop_all_protos(cls):
        for v in _active_protos.values():
            if v[0] is not None:
                cls._stop(v[1], v[0])
                v[0] = None

    def start(self):
        global _active_protos
        self.ensure_one()
        if not self.enabled:
            return
        id_ = str(self)
        if id_ not in _active_protos:
            _active_protos[id_] = [None, {"user": {}}]
        # already running
        if _active_protos[id_][0] is not None:
            return
        _active_protos[id_][0] = self._start(_active_protos[id_][1])

    def stop(self):
        global _active_protos
        self.ensure_one()
        id_ = str(self)
        if id_ in _active_protos and _active_protos[id_][0] is not None:
            self._stop(_active_protos[id_][1], _active_protos[id_][0])
            _active_protos[id_][0] = None

    def restart(self):
        self.stop()
        self.start()


@orm.register_model
class LoraModem(sillyorm.model.Model):
    _name = "lora_modem"

    name = sillyorm.fields.String(required=True)

    # link to protocol (one modem always only linked to none or one protocol, since it's multiple protocols we can't represent this as normal Many2one links)
    proto_model = sillyorm.fields.String()
    proto_id = sillyorm.fields.Integer()

    # modem settings fields

    modem_type = sillyorm.fields.Selection(["serial", "ip"], required=True)

    serial_port = sillyorm.fields.String(length=255)

    ip_host = sillyorm.fields.String()
    ip_port = sillyorm.fields.Integer()

    # lora settings
    lora_gain = sillyorm.fields.Integer(required=True, default=0)
    lora_tx_power = sillyorm.fields.Integer(required=True, default=0)

    @sillyorm.model.constraints("proto_model", "proto_id")
    def _proto_link_check(self):
        for record in self:
            if not (record.proto_model is None) == (record.proto_id is None):
                raise Exception("both proto_model and proto_id must be set at the same time")
            if record.proto_model is not None and record.env[record.proto_model].browse(record.proto_id) is None:
                raise Exception("linked proto record could not be found")
            if record.proto_model is not None and record.env[record.proto_model].browse(record.proto_id).modem_id.id != self.id:
                raise Exception("linked proto record does not point to modem")

    @sillyorm.model.constraints("lora_gain", "lora_tx_power")
    def _check_lora_settings(self):
        for record in self:
            if record.lora_gain < 0 or record.lora_gain > 10:
                raise Exception(f"invalid lora_gain {record.lora_gain}")
            if record.lora_tx_power < 0:
                raise Exception(f"invalid lora_tx_power {record.lora_tx_power}")

    def proto_link(self, proto):
        self.ensure_one()
        if self.proto_model is not None:
            raise Exception("cannot link already linked proto")
        proto.env._common_proto_write_modem_id_ignore = True
        proto.modem_id = self
        proto.env._common_proto_write_modem_id_ignore = None
        self.write({
            "proto_model": proto._name,
            "proto_id": proto.id,
        })

    def proto_unlink(self):
        self.ensure_one()
        self.env._common_proto_write_modem_id_ignore = True
        self.env[self.proto_model].browse(self.proto_id).modem_id = None
        self.env._common_proto_write_modem_id_ignore = None
        self.write({
            "proto_model": None,
            "proto_id": None,
        })

    @sillyorm.model.constraints("modem_type")
    def _modem_type_check(self):
        for record in self:
            match record.modem_type:
                case "serial":
                    if record.serial_port is None:
                        raise Exception("LoraModem type serial needs serial_port set")
                case "ip":
                    if record.ip_host is None or record.ip_port is None:
                        raise Exception("LoraModem type ip needs host and port set")

    def get_instance(self):
        self.ensure_one()
        match self.modem_type:
            case "serial":
                inst = esplora.ESPLoraSerial(self.serial_port)
            case "ip":
                inst = esplora.ESPLoraWifi(host=self.ip_host, port=self.ip_port)
            case _:
                raise Exception(f"unsupported modem type {self.modem_type}")

        inst.set_gain(self.lora_gain)
        inst.set_tx_power(self.lora_tx_power)

        return inst

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.DEBUG
)

@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    orm.init()
    meshcore_api.startup()
    yield
    ProtoCommon.stop_all_protos()

app = fastapi.FastAPI(lifespan=lifespan)

app.include_router(meshcore_api.router, prefix="/meshcore")
