from core.scheduler import Scheduler
from core.logger import Logger

def clear_expired_sessions():
    Logger.info("Scheduled job: Clearing expired sessions...")
    # clear sessions logic can go here

def backup_database():
    Logger.info("Scheduled job: Backing up database...")
    # backup logic can go here

# Register scheduled tasks
Scheduler.call(clear_expired_sessions).every_minute()
Scheduler.call(backup_database).daily("02:00")
