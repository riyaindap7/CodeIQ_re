# file_queue.py
import asyncio
import aiofiles
import os
from typing import List, Set, Callable, Optional, Any
from dataclasses import dataclass
from pathlib import Path

@dataclass
class FileTask:
    path: str
    ast: Optional[Any] = None

    @property
    def file_path(self) -> str:
        # backward-compat alias for older code expecting .file_path
        return self.path

class FileQueue:
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.queue = asyncio.Queue()
        self.processed_files: Set[str] = set()
        
    async def add_file(self, file_path: str):
        if file_path not in self.processed_files:
            # match dataclass field name 'path'
            await self.queue.put(FileTask(path=file_path))
            self.processed_files.add(file_path)
    
    async def get_file(self) -> FileTask:
        return await self.queue.get()
    
    def task_done(self):
        self.queue.task_done()
    
    async def wait_completion(self):
        await self.queue.join()