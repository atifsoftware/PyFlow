"""
public/index.py
================
প্রোডাকশন WSGI এন্ট্রি পয়েন্ট। gunicorn / uWSGI / mod_wsgi যেকোনো WSGI সার্ভার
এই ফাইলের 'application' অবজেক্টকে টার্গেট করবে।

    gunicorn --chdir /path/to/pyflow public.index:application

ডেভেলপমেন্টে সরাসরি চালাতে চাইলে প্রজেক্ট রুট থেকে: python run.py
"""

import sys
import os

# প্রজেক্ট রুট sys.path-এ যোগ করা হচ্ছে যাতে core/app/config ইমপোর্ট করা যায়
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from core.application import Application
from config.config import get_config
from config.routes import build_router

config = get_config()
router = build_router()
application = Application(router, config)

