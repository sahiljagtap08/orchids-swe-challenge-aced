import asyncio
from typing import Dict, List, Callable

_job_logs: Dict[str, List[str]] = {}
_log_listeners: Dict[str, List[asyncio.Queue]] = {}


class JobLogger:
    def __init__(self, job_id: str, queue: asyncio.Queue):
        self.job_id = job_id
        self.queue = queue

    async def log_message(self, message: str, type: str = "info"):
        """
        Logs a message to the job's SSE queue.
        Uses specific emoji prefixes for structured logging on the frontend.
        """
        
        # Map message types to prefixes
        prefix_map = {
            "header": "🚀",
            "success": "✅",
            "error": "ERROR:",
            "asset": "📦",
            "ai": "🧠",
            "sparkle": "✨",
            "page": "📄",
            "info": ">",
            "sub-item": "- ",
            "code": "CODE:"
        }
        
        prefix = prefix_map.get(type, ">")
        
        log_message = f"{prefix} {message}".strip()

        try:
            await self.queue.put(log_message)
        except Exception as e:
            # This might happen if the client disconnects
            print(f"Error putting log message in queue for job {self.job_id}: {e}")
        
        # Optional: Print to server console for debugging
        # print(f"[{self.job_id[:8]}] {log_message}")

# Global queue for SSE
log_queue = asyncio.Queue()

# In-memory store for job-specific queues
job_queues: dict[str, asyncio.Queue] = {}

def get_job_logger(job_id: str) -> JobLogger:
    """
    Creates or retrieves a logger for a specific job.
    """
    if job_id not in job_queues:
        job_queues[job_id] = asyncio.Queue()
    return JobLogger(job_id, job_queues[job_id])

def cleanup_job_logger(job_id: str):
    """
    Removes a job's logger from memory.
    """
    if job_id in job_queues:
        # To prevent memory leaks, we can put a sentinel value
        # or just remove it if we're sure it's done.
        del job_queues[job_id]
        print(f"Cleaned up logger for job {job_id}")

async def log_generator(job_id: str):
    """
    Yields log messages for a given job ID.
    """
    if job_id not in job_queues:
        # This can happen if the client requests logs for a job that doesn't exist
        # or has already been cleaned up.
        return

    q = job_queues[job_id]
    try:
        while True:
            log_message = await q.get()
            if log_message is None:  # Sentinel value to end logging
                break
            yield log_message
            q.task_done()
    except asyncio.CancelledError:
        print(f"Log generator for job {job_id} was cancelled.")
    finally:
        # The generator is done, so we can clean up the queue
        cleanup_job_logger(job_id)

class LiveLogger:
    """A class to handle real-time logging for background jobs using SSE"""

    def __init__(self, job_id: str):
        self.job_id = job_id
        if self.job_id not in _job_logs:
            _job_logs[self.job_id] = []
        if self.job_id not in _log_listeners:
            _log_listeners[self.job_id] = []

    async def log(self, message: str):
        """Adds a log message and notifies all active listeners."""
        
        log_message = f"[{self.job_id[:8]}] {message}"
        print(log_message)  # Also print to server console for debugging
        
        _job_logs[self.job_id].append(message)
        
        # Notify all listeners for this job
        if self.job_id in _log_listeners:
            for queue in _log_listeners[self.job_id]:
                await queue.put(message)

    @staticmethod
    async def subscribe(job_id: str):
        """
        A generator that yields logs for a specific job for SSE.
        First, it yields all historical logs, then waits for new ones.
        """
        queue = asyncio.Queue()
        if job_id not in _log_listeners:
            _log_listeners[job_id] = []
        _log_listeners[job_id].append(queue)
        
        try:
            # Yield all existing logs for this job
            if job_id in _job_logs:
                for log in _job_logs[job_id]:
                    yield f"data: {log}\n\n"
                    await asyncio.sleep(0.01)

            # Wait for new logs and yield them
            while True:
                log = await queue.get()
                yield f"data: {log}\n\n"
                if log == "[END]":
                    break
        finally:
            # Clean up the queue when the client disconnects or stream ends
            if queue in _log_listeners.get(job_id, []):
                _log_listeners[job_id].remove(queue)

    @staticmethod
    def cleanup(job_id: str):
        """Cleans up logs and listeners for a completed or failed job."""
        if job_id in _job_logs:
            del _job_logs[job_id]
        if job_id in _log_listeners:
            del _log_listeners[job_id] 