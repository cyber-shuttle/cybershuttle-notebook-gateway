class APIBase:

    def __init__(self, **kwargs) -> None:
        pass


from .slurm import SlurmAPI


def get_class_by_name(name: str) -> type[APIBase]:
    if name == "slurm":
        return SlurmAPI
    raise ValueError(name)
