import asyncio
from typing import Dict, Union


class Queue:
    def __init__(self, file_name: str, file_size: int, enabled: bool = True):
        self.file_name = file_name
        self.file_size = file_size
        self.enabled = enabled

    def disable(self):
        self.enabled = False


class bot_user:
    def __init__(self):
        """
        bot user class
        has its own tasks list, own queue and asyncio locks for queueing tasks, besides personal bot configs, etc.
        """
        self.tasks: Dict[int, Union[asyncio.Task, None]] = {0: None}
        self.tasksLock = asyncio.Lock()
        self.oneFileLock = asyncio.Lock()
        self.queue_dict: Dict[int, Queue] = {}

        self.options: Dict[str, any] = {
            "verbose": False,
            "checksum": True,
        }

    def get_tasks(self):
        return sum(bool(self.queue_dict[key].enabled) for key in self.queue_dict), sum(
            self.queue_dict[key].file_size for key in self.queue_dict
        )

    def __repr__(self):
        return f"<{self.__class__.__module__}.{self.__class__.__name__} object at {hex(id(self))}>\ntasks: {self.get_tasks()}\n"
