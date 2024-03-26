from . import TransportBase


class KafkaTransport(TransportBase):

    def __init__(self) -> None:
        super().__init__()
