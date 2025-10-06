# file_queue.py
import asyncio
import aiofiles
import os
from typing import List, Set, Callable, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# NOTE: Optional and Any must come from the typing module. They were
# incorrectly imported from `pyparsing`, which defines its own `Any`/`Opt`
# types that are not compatible with Python typing subscripting (causing
# "type 'Opt' is not subscriptable"). Importing from `typing` fixes this.

@dataclass
class FileTask:
    file_path: str
    content: str = ""
    ast: Optional[Any] = None

class FileQueue:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.queue = asyncio.Queue()
        self.processed_files: Set[str] = set()
        
    async def add_file(self, file_path: str):
        if file_path not in self.processed_files:
            await self.queue.put(FileTask(file_path=file_path))
            self.processed_files.add(file_path)
    
    async def get_file(self) -> FileTask:
        return await self.queue.get()
    
    def task_done(self):
        self.queue.task_done()
    
    async def wait_completion(self):
        await self.queue.join()