import abc
import threading
from typing import Any, Dict


class Singleton(abc.ABCMeta):
    """Singleton Abstract Base Class
    https://stackoverflow.com/questions/33364070/implementing\
        -singleton-as-metaclass-but-for-abstract-classes
    """

    _instances: Dict[Any, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class ThreadSafeSingleton(abc.ABCMeta):
    """Thread Safe Singleton Abstract Base Class

    https://stackoverflow.com/questions/33364070/implementing\
        -singleton-as-metaclass-but-for-abstract-classes
    https://medium.com/analytics-vidhya/how-to-create-\
        a-thread-safe-singleton-class-in-python-822e1170a7f6
    """

    _instances: Dict[Any, Any] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super(ThreadSafeSingleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]
