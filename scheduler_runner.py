import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.config import get_config
from core.database import Database
from core.scheduler import Scheduler
# Import app/scheduler to register tasks
import app.scheduler

if __name__ == "__main__":
    config = get_config()
    Database.init(config)
    Scheduler.start()
