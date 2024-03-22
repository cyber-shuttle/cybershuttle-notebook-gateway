class TransportBase:

    def __init__(self, **kwargs) -> None:
        pass


from .grpc import GrpcTransport
from .kafka import KafkaTransport
from .websocket import WebsocketTransport
from .zmq import ZMQTransport


def get_class_by_name(name: str) -> type[TransportBase]:
    if name == "grpc":
        return GrpcTransport
    if name == "kafka":
        return KafkaTransport
    if name == "websocket":
        return WebsocketTransport
    if name == "zmq":
        return ZMQTransport
    raise ValueError(name)
