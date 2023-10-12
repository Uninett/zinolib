"""
Deprecated: import from zinolib.controllers.zino1 directly
"""

from .controllers.zino1 import EventAdapter, HistoryAdapter, LogAdapter, Zino1EventManager, HistoryDict, LogDict


Zino1EventEngine = Zino1EventManager


__all__ = [
    "EventAdapter",
    "HistoryAdapter",
    "LogAdapter",
    "Zino1EventEngine",
    "Zino1EventManager",
    "HistoryDict",
    "LogDict",
]
