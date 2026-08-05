import sys
import os

# ১. প্রজেক্ট রুট পাথ সিস্টেম পাথে যুক্ত করা
sys.path.insert(0, os.path.dirname(__file__))

# ২. WSGI অ্যাপ্লিকেশন ইমপোর্ট করা (public/index.py থেকে)
from public.index import application



