from cybershuttle_gateway.transport import TransportBase


class WebsocketTransport(TransportBase):

    def __init__(self) -> None:
        super().__init__()
