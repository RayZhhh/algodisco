# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from abc import abstractmethod, ABC
from typing import Dict, Any


class AlgoSearchLoggerBase(ABC):

    @abstractmethod
    async def log_dict(self, log_item: Dict, item_name: str): ...

    async def finish(self): ...

    def set_log_item_flush_frequency(self, *args, **kwargs): ...

    # Sync versions
    def log_dict_sync(self, log_item: Dict, item_name: str):
        """Synchronous version of log_dict. Override in subclass if needed."""
        raise NotImplementedError("Sync version not implemented for this logger")

    def finish_sync(self):
        """Synchronous version of finish. Override in subclass if needed."""
        pass
