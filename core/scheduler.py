import time
import datetime
import threading
from core.logger import Logger

class Task:
    def __init__(self, callback, args=None, kwargs=None):
        self.callback = callback
        self.args = args or ()
        self.kwargs = kwargs or {}
        self.interval_seconds = None
        self.daily_time = None  # (hour, minute)
        self.last_run = 0

    def every_minute(self):
        self.interval_seconds = 60
        return self

    def every_five_minutes(self):
        self.interval_seconds = 300
        return self

    def hourly(self):
        self.interval_seconds = 3600
        return self

    def daily(self, time_str="00:00"):
        """Schedule a daily task at 'HH:MM' (e.g. '14:30')"""
        parts = time_str.split(":")
        self.daily_time = (int(parts[0]), int(parts[1]))
        return self

    def should_run(self, now) -> bool:
        if self.interval_seconds:
            return (now - self.last_run) >= self.interval_seconds
            
        if self.daily_time:
            now_dt = datetime.datetime.fromtimestamp(now)
            last_dt = datetime.datetime.fromtimestamp(self.last_run) if self.last_run else None
            
            # Target run time for today
            target_dt = now_dt.replace(hour=self.daily_time[0], minute=self.daily_time[1], second=0, microsecond=0)
            
            # If target has passed and we haven't run today yet, or last run was on a previous day
            if now_dt >= target_dt:
                if last_dt is None or last_dt.date() < now_dt.date():
                    return True
        return False

    def run(self):
        self.last_run = int(time.time())
        try:
            Logger.info(f"Running scheduled task: {self.callback.__name__}")
            self.callback(*self.args, **self.kwargs)
        except Exception as e:
            Logger.error(f"Scheduled task {self.callback.__name__} failed: {e}")

class Scheduler:
    _tasks = []
    _running = False

    @classmethod
    def call(cls, callback, *args, **kwargs) -> Task:
        """Register a new scheduled task"""
        task = Task(callback, args, kwargs)
        cls._tasks.append(task)
        return task

    @classmethod
    def run_pending(cls):
        """Check and execute all pending tasks"""
        now = int(time.time())
        for task in cls._tasks:
            if task.should_run(now):
                task.run()

    @classmethod
    def start(cls, sleep_interval=1):
        """Start scheduler main loop in current thread"""
        cls._running = True
        Logger.info("Task Scheduler started...")
        try:
            while cls._running:
                cls.run_pending()
                time.sleep(sleep_interval)
        except KeyboardInterrupt:
            Logger.info("Task Scheduler stopped by user.")
        finally:
            cls._running = False

    @classmethod
    def start_daemon(cls, sleep_interval=1):
        """Start scheduler as a background daemon thread"""
        if cls._running:
            return
            
        t = threading.Thread(target=cls.start, args=(sleep_interval,), daemon=True)
        t.start()
