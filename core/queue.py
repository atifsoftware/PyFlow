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
        
        sql = """
            INSERT INTO jobs (queue, payload, attempts, reserved_at, available_at, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """ if Database.driver == "mysql" else """
            INSERT INTO jobs (queue, payload, attempts, reserved_at, available_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
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
        
        select_sql = """
            SELECT id, payload, attempts FROM jobs
            WHERE queue = %s AND reserved_at IS NULL AND available_at <= %s
            ORDER BY id ASC LIMIT 1
        """ if Database.driver == "mysql" else """
            SELECT id, payload, attempts FROM jobs
            WHERE queue = ? AND reserved_at IS NULL AND available_at <= ?
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
            update_sql = """
                UPDATE jobs SET reserved_at = %s, attempts = attempts + 1
                WHERE id = %s AND reserved_at IS NULL
            """ if Database.driver == "mysql" else """
                UPDATE jobs SET reserved_at = ?, attempts = attempts + 1
                WHERE id = ? AND reserved_at IS NULL
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
        sql = "DELETE FROM jobs WHERE id = %s" if Database.driver == "mysql" else "DELETE FROM jobs WHERE id = ?"
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
        sql = """
            UPDATE jobs SET reserved_at = NULL, available_at = %s
            WHERE id = %s
        """ if Database.driver == "mysql" else """
            UPDATE jobs SET reserved_at = NULL, available_at = ?
            WHERE id = ?
        """
        try:
            Database.execute(sql, (available_at, job_id))
            Database.commit()
        except Exception as e:
            Logger.error(f"Failed to release job {job_id}: {e}")
