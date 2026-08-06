"""
tests/test_di.py
================
IoC Container এবং Dependency Injection এর ইউনিট টেস্ট।
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.container import Container
from core.controller import action
from core.application import Application
from config.routes import build_router


# ডামি ক্লাসসমূহ
class DBService:
    def get_data(self):
        return "db_data"


class PaymentGateway:
    def __init__(self, db: DBService):
        self.db = db

    def pay(self):
        return f"paid with {self.db.get_data()}"


class OrderService:
    def __init__(self, gateway: PaymentGateway):
        self.gateway = gateway


class DummyController:
    def __init__(self, request, session, view_engine, order: OrderService):
        self.request = request
        self.session = session
        self.view_engine = view_engine
        self.order = order

    def index(self):
        return self.order.gateway.pay()


class DependencyInjectionTest(PyFlowTestCase):

    def test_container_bindings_and_resolving(self):
        container = Container()

        # ১. সাধারণ বাইন্ডিং
        container.bind(DBService)
        db1 = container.resolve(DBService)
        db2 = container.resolve(DBService)
        
        self.assertIsInstance(db1, DBService)
        self.assertNotEqual(id(db1), id(db2)) # singleton না হলে আলাদা ইনস্ট্যান্স হবে

        # ২. সিঙ্গেলটন বাইন্ডিং
        container.singleton(PaymentGateway)
        pg1 = container.resolve(PaymentGateway)
        pg2 = container.resolve(PaymentGateway)

        self.assertEqual(id(pg1), id(pg2)) # একই ইনস্ট্যান্স হতে হবে
        self.assertEqual(pg1.pay(), "paid with db_data")

    def test_container_autowiring(self):
        container = Container()
        # কোনো বাইন্ডিং ছাড়াই সরাসরি রিজলভ করার চেষ্টা করি (Autowiring)
        order = container.resolve(OrderService)

        self.assertIsInstance(order, OrderService)
        self.assertIsInstance(order.gateway, PaymentGateway)
        self.assertIsInstance(order.gateway.db, DBService)
        self.assertEqual(order.gateway.pay(), "paid with db_data")

    def test_controller_dependency_injection(self):
        # Application বুট করি যা Container যুক্ত করবে
        router = build_router()
        app = Application(router, self._test_config)

        # কন্ট্রোলার অ্যাকশন জেনারেট করি
        handler = action(DummyController, "index")

        # ডামি রিকোয়েস্ট ভ্যারিয়েবল
        from core.request import Request
        from core.session import Session
        
        dummy_req = Request({"REQUEST_METHOD": "GET", "PATH_INFO": "/"})
        dummy_sess = Session()
        
        # অ্যাকশন কল করি
        response = handler(dummy_req, dummy_sess, app.view_engine)

        # ভ্যালু সঠিক এসেছে কিনা তা যাচাই করি
        self.assertEqual(response, "paid with db_data")


if __name__ == "__main__":
    import unittest
    unittest.main()
