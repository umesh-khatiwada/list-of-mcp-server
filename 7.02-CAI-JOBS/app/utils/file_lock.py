
import fcntl
import os
import time
import logging

logger = logging.getLogger(__name__)

class FileLock:
    """
    A context manager for file locking using fcntl.
    Ensures that only one process/thread can access the file at a time.
    """
    def __init__(self, lock_file_path: str, timeout: float = 10.0):
        self.lock_file_path = lock_file_path + ".lock"
        self.timeout = timeout
        self.fd = None

    def __enter__(self):
        start_time = time.time()
        self.fd = open(self.lock_file_path, 'w')
        
        while True:
            try:
                # Try to acquire an exclusive lock (non-blocking)
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except (IOError, OSError):
                # If lock is held by another process, wait and retry
                if time.time() - start_time >= self.timeout:
                    self.fd.close()
                    raise TimeoutError(f"Could not acquire lock for {self.lock_file_path} within {self.timeout} seconds")
                time.sleep(0.1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            # Release the lock
            fcntl.flock(self.fd, fcntl.LOCK_UN)
        except Exception as e:
            logger.error(f"Error releasing lock for {self.lock_file_path}: {e}")
        finally:
            self.fd.close()
            # Optional: Remove lock file, but risky if others are waiting on it. 
            # Better to leave it for persistence or clean up periodically.
            # os.unlink(self.lock_file_path) 
