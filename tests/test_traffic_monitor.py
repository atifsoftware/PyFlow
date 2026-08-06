"""
tests/test_traffic_monitor.py
==============================
DDoS Traffic Monitor এবং DoS Block লগার টেস্ট।
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.security import TrafficMonitor, RateLimiter
from core.request import Request
from app.models.activity_log_model import ActivityLog


class DummyRequest:
    def __init__(self, ip="127.0.0.1", path="/", user_agent="Mozilla/5.0"):
        self._ip = ip
        self._path = path
        self._user_agent = user_agent
        self.method = "GET"

    def ip(self):
        return self._ip

    def path(self):
        return self._path

    def header(self, name, default=None):
        if name.lower() == "user-agent":
            return self._user_agent
        return default


class TrafficMonitorTest(PyFlowTestCase):

    def setUp(self):
        super().setUp()
        # Reset hits for clean state
        TrafficMonitor._global_hits = []
        TrafficMonitor._last_alert_time = 0
        RateLimiter._hits = {}

    def test_record_hit_increments_count(self):
        req = DummyRequest(ip="192.168.1.1")
        
        c1 = TrafficMonitor.record_hit(req, max_global_rpm=10)
        c2 = TrafficMonitor.record_hit(req, max_global_rpm=10)
        
        self.assertEqual(c1, 1)
        self.assertEqual(c2, 2)

    def test_record_hit_triggers_ddos_alert_when_exceeds_threshold(self):
        req = DummyRequest(ip="192.168.1.5")
        
        # Hit 5 times, threshold is 4
        for i in range(5):
            TrafficMonitor.record_hit(req, max_global_rpm=4)
            
        # Verify that a ddos_alert log is recorded in the activity_logs table
        alerts = ActivityLog.query().where("action", "ddos_alert").get()
        self.assertGreaterEqual(len(alerts), 1)
        self.assertIn("রিকোয়েস্ট", alerts[0]["description"])
        
    def test_global_rate_limiter_block_logs_dos_block(self):
        from core.application import Application
        from config.routes import build_router
        
        config = {
            "APP_NAME": "Test App",
            "LOG_FILE": "storage/logs/test.log",
            "DDOS_THRESHOLD_RPM": "10",
        }
        app = Application(build_router(), config)
        
        # Mock request with IP
        environ = {
            "PATH_INFO": "/",
            "REQUEST_METHOD": "GET",
            "REMOTE_ADDR": "1.2.3.4",
            "HTTP_USER_AGENT": "TestBot",
        }
        
        # Hit global rate limiter (300 limit in 60s)
        # We hit 301 times to trigger block
        RateLimiter._hits = {}
        
        for _ in range(300):
            app._handle_request(environ)
            
        # 301st request should be blocked (429)
        response = app._handle_request(environ)
        self.assertEqual(response.status_code, 429)
        
        # Verify that dos_block is logged in activity_logs
        blocks = ActivityLog.query().where("action", "dos_block").get()
        self.assertGreaterEqual(len(blocks), 1)
        self.assertIn("1.2.3.4", blocks[0]["description"])


if __name__ == "__main__":
    import unittest
    unittest.main()
