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
    """Thread Safe Singleton

    https://medium.com/analytics-vidhya/how-to-create-\
        a-thread-safe-singleton-class-in-python-822e1170a7f6
    """

    _instances: dict[Any, tuple[Any, threading.Lock]] = {}
    _lock = threading.Lock()  # Ensures thread safety

    def __call__(cls, *args, **kwargs):
        cls._lock.acquire()
        if cls not in cls._instances:
            cls._instances[cls] = (None, threading.Lock())
        cls._instances[cls][1].acquire()
        cls._lock.release()
        if cls._instances[cls][0] is None:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = (instance, cls._instances[cls][1])
        cls._instances[cls][1].release()
        return cls._instances[cls][0]
