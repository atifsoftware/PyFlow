"""
tests/test_modules.py
======================
Service Provider এবং মডিউল অটো-ডিসকভারি সিস্টেমের ইউনিট টেস্ট।
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.application import Application
from config.routes import build_router
from core.view import ViewError


class ModuleSystemTest(PyFlowTestCase):

    def test_module_auto_discovery_and_booting(self):
        # Application বুট করার সময় module_manager ডাইনামিকালি modules/inventory লোড করবে
        router = build_router()
        app = Application(router, self._test_config)
        
        # ১. যাচাই করি module_manager তৈরি হয়েছে কিনা
        self.assertTrue(hasattr(app, "module_manager"))
        
        # ২. যাচাই করি inventory মডিউলটি লোড হয়েছে কিনা
        self.assertIn("inventory", app.module_manager.modules)
        
        # ৩. যাচাই করি প্রোভাইডার রেজিস্টার হয়েছে কিনা
        provider_names = [p.__class__.__name__ for p in app.module_manager.providers]
        self.assertIn("InventoryServiceProvider", provider_names)
        
        # ৪. ভিউ নেমস্পেস রেজিস্টার হয়েছে কিনা চেক করি
        self.assertIn("inventory", app.view_engine.namespaces)
        
        # ৫. রাউট রেজিস্ট্রি চেক করি (router-এ /inventory রাউট যুক্ত হয়েছে কিনা)
        route_paths = [route.raw_pattern for route in router.routes]
        self.assertIn("/inventory", route_paths)

    def test_modular_view_rendering_with_namespace(self):
        app = Application(build_router(), self._test_config)
        
        # সরাসরি ভিউ ইঞ্জিনের মাধ্যমে নেমস্পেস ভিউ রেন্ডার করি
        html = app.view_engine.render("inventory::dashboard", {
            "title": "Test Title",
            "items": ["Item A", "Item B"]
        })
        
        self.assertIn("<title>Test Title</title>", html)
        self.assertIn("<li>Item A</li>", html)
        self.assertIn("<li>Item B</li>", html)

    def test_invalid_namespace_raises_error(self):
        app = Application(build_router(), self._test_config)
        
        # ভুল নেমস্পেস দিলে ViewError আসতে হবে
        with self.assertRaises(ViewError):
            app.view_engine.render("invalid_ns::dashboard", {"title": "X", "items": []})


if __name__ == "__main__":
    import unittest
    unittest.main()
