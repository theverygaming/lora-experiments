import contextlib
import logging
import os
import sillyorm
import threading

_tlocal_orm = threading.local()


def _init_registry():
    db_file = os.environ.get("DB_FILE", "db.sqlite3")
    reg = sillyorm.Registry(f"sqlite:///{db_file}")
    for model in register_model._models:
        reg.register_model(model)
    reg.resolve_tables()
    reg.init_db_tables(automigrate="auto")
    return reg


def registry():
    reg = getattr(_tlocal_orm, "registry", None)
    if reg is None:
        reg = _init_registry()
        _tlocal_orm.registry = reg
    return reg


def register_model(cls):
    register_model._models.append(cls)
    return cls
register_model._models = []


def init():
    # FIXME: use migrations
    registry()


# fastapi dependency
def env() -> sillyorm.Environment:
    with registry().environment() as env_:
        with env_.transaction():
            yield env_


@contextlib.contextmanager
def env_ctx():
    yield from env()
