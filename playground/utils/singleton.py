import abc
from typing import Any, Dict


class Singleton(abc.ABCMeta):
    """Singleton Abstract Base Class

    https://stackoverflow.com/questions/33364070/implementing
    -singleton-as-metaclass-but-for-abstract-classes
    """

    _instances: Dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
