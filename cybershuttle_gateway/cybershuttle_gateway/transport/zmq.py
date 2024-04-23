from cybershuttle_gateway.transport import TransportBase


class ZMQTransport(TransportBase):

    def __init__(self) -> None:
        super().__init__()
