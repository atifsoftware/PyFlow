import time
import json
import importlib
from core.database import Database
from core.logger import Logger

class Queue:
    @classmethod
    def push(cls, job_class, data, queue="default", delay=0):
        """Push a job onto the database queue"""
        class_path = f"{job_class.__module__}.{job_class.__name__}"
        payload = json.dumps({
            "class": class_path,
            "data": data
        }, ensure_ascii=False)
        
        now = int(time.time())
        available_at = now + delay
        
        ph = Database.placeholder()
        sql = f"""
            INSERT INTO jobs (queue, payload, attempts, reserved_at, available_at, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})
        """
        
        try:
            Database.execute(sql, (queue, payload, 0, None, available_at, now))
            Database.commit()
            Logger.debug(f"Job {class_path} pushed to queue '{queue}'")
        except Exception as e:
            Logger.error(f"Failed to push job to queue: {e}")
            raise

    @classmethod
    def pop(cls, queue="default"):
        """Pop a job off the queue, reserving it atomically"""
        now = int(time.time())
        ph = Database.placeholder()
        
        select_sql = f"""
            SELECT id, payload, attempts FROM jobs
            WHERE queue = {ph} AND reserved_at IS NULL AND available_at <= {ph}
            ORDER BY id ASC LIMIT 1
        """
        
        try:
            cursor = Database.execute(select_sql, (queue, now))
            row = cursor.fetchone()
            if not row:
                return None
                
            if isinstance(row, dict):
                job_id = row["id"]
                payload_str = row["payload"]
                attempts = row["attempts"]
            else:
                job_id = row[0]
                payload_str = row[1]
                attempts = row[2]
                
            # Attempt to reserve job (compare-and-swap update)
            update_sql = f"""
                UPDATE jobs SET reserved_at = {ph}, attempts = attempts + 1
                WHERE id = {ph} AND reserved_at IS NULL
            """
            
            cursor = Database.execute(update_sql, (now, job_id))
            Database.commit()
            
            if cursor.rowcount > 0:
                payload = json.loads(payload_str)
                return {
                    "id": job_id,
                    "class_path": payload["class"],
                    "data": payload["data"],
                    "attempts": attempts + 1
                }
            return None
        except Exception as e:
            Logger.error(f"Failed to pop job from queue: {e}")
            return None

    @classmethod
    def delete(cls, job_id):
        """Delete a completed job from the queue"""
        ph = Database.placeholder()
        sql = f"DELETE FROM jobs WHERE id = {ph}"
        try:
            Database.execute(sql, (job_id,))
            Database.commit()
        except Exception as e:
            Logger.error(f"Failed to delete job {job_id}: {e}")

    @classmethod
    def release(cls, job_id, delay=0):
        """Release a failed job back onto the queue with an optional delay"""
        now = int(time.time())
        available_at = now + delay
        ph = Database.placeholder()
        sql = f"""
            UPDATE jobs SET reserved_at = NULL, available_at = {ph}
            WHERE id = {ph}
        """
        try:
            Database.execute(sql, (available_at, job_id))
            Database.commit()
        except Exception as e:
            Logger.error(f"Failed to release job {job_id}: {e}")
