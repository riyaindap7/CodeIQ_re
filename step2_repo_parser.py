# repository_parser.py
import asyncio
import aiofiles
import os
from git import Repo
from pathlib import Path
from typing import List, Set, Dict
from step1_file_queue import FileQueue, FileTask
import tempfile
import shutil

class RepositoryParser:
    def __init__(self, max_workers: int = 4):
        self.file_queue = FileQueue(max_workers)
        self.supported_extensions = {'.py', '.js', '.java', '.cpp', '.c', '.ts'}
        
    async def clone_repository(self, repo_url: str, local_path: str) -> str:
        """Clone repository to local path"""
        if os.path.exists(local_path):
            shutil.rmtree(local_path)
            
        print(f"Cloning repository: {repo_url}")
        Repo.clone_from(repo_url, local_path)
        return local_path
    
    async def discover_files(self, repo_path: str) -> List[str]:
        """Discover all code files in repository"""
        code_files = []
        
        for root, dirs, files in os.walk(repo_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                file_path = os.path.join(root, file)
                if self._is_code_file(file_path):
                    code_files.append(file_path)
        
        print(f"Discovered {len(code_files)} code files")
        return code_files
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file based on extension"""
        return any(file_path.endswith(ext) for ext in self.supported_extensions)
    
    async def read_file_content(self, file_path: str) -> str:
        """Read file content asynchronously"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
            return content
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return ""
    
    async def process_repository(self, repo_url: str) -> Dict[str, str]:
        """Main method to process repository"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = await self.clone_repository(repo_url, os.path.join(temp_dir, "repo"))
            files = await self.discover_files(repo_path)
            
            # Add files to queue
            for file_path in files:
                await self.file_queue.add_file(file_path)
            
            # Process files
            file_contents = {}
            workers = [
                asyncio.create_task(self._file_worker(file_contents))
                for _ in range(self.file_queue.max_workers)
            ]
            
            await self.file_queue.wait_completion()
            
            # Cancel workers
            for worker in workers:
                worker.cancel()
            
            print(f"Processed {len(file_contents)} files")
            return file_contents
    
    async def _file_worker(self, file_contents: Dict[str, str]):
        """Worker to process files from queue"""
        while True:
            try:
                file_task = await asyncio.wait_for(self.file_queue.get_file(), timeout=1.0)
                
                content = await self.read_file_content(file_task.file_path)
                if content:
                    file_contents[file_task.file_path] = content
                
                self.file_queue.task_done()
                
            except asyncio.TimeoutError:
                break
            except Exception as e:
                print(f"Worker error: {e}")
                self.file_queue.task_done()