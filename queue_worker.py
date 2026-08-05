import os
import sys
import time
import importlib
import traceback

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.config import get_config
from core.database import Database
from core.queue import Queue
from core.logger import Logger

def execute_job(job):
    class_path = job["class_path"]
    data = job["data"]
    job_id = job["id"]
    attempts = job["attempts"]
    
    try:
        module_name, class_name = class_path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        job_class = getattr(module, class_name)
        
        Logger.info(f"Processing job {class_path} (Attempt {attempts})...")
        
        # Instantiate and run
        instance = job_class()
        instance.handle(data)
        
        # Success, delete job
        Queue.delete(job_id)
        Logger.info(f"[OK] Job {class_path} completed successfully.")
    except Exception as e:
        Logger.error(f"Job {class_path} failed: {e}\n{traceback.format_exc()}")
        if attempts >= 3:
            Logger.critical(f"Job {class_path} failed after maximum attempts. Deleting from queue.")
            Queue.delete(job_id)
        else:
            # Retry with 10 second delay
            retry_delay = 10
            Logger.warning(f"Releasing job {class_path} for retry in {retry_delay} seconds.")
            Queue.release(job_id, delay=retry_delay)

def start_worker(queue="default", sleep_seconds=1):
    config = get_config()
    Database.init(config)
    Logger.info(f"Queue Worker started on queue '{queue}'...")
    
    try:
        while True:
            job = Queue.pop(queue)
            if job:
                execute_job(job)
            else:
                time.sleep(sleep_seconds)
    except KeyboardInterrupt:
        Logger.info("Queue Worker stopped by user.")
    finally:
        Database.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="PyFlow Queue Worker")
    parser.add_argument("--queue", default="default", help="Queue name to process")
    parser.add_argument("--sleep", type=int, default=1, help="Sleep time when queue is empty")
    args = parser.parse_args()
    
    start_worker(queue=args.queue, sleep_seconds=args.sleep)
