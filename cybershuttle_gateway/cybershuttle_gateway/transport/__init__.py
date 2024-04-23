class TransportBase:

    def __init__(self, **kwargs) -> None:
        pass


from cybershuttle_gateway.transport.grpc import GrpcTransport
from cybershuttle_gateway.transport.kafka import KafkaTransport
from cybershuttle_gateway.transport.websocket import WebsocketTransport
from cybershuttle_gateway.transport.zmq import ZMQTransport


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
