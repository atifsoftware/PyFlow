"""
tests/test_form_request.py
==========================
Unit tests for FormRequest and DTO Validation Layer in PyFlow.
"""

import sys
import os
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.testing import PyFlowTestCase
from core.request import Request
from core.session import Session
from core.response import Response
from core.controller import Controller, action
from core.form_request import FormRequest, ValidationException, AuthorizationException


class CreateCustomerRequest(FormRequest):
    def rules(self):
        return {
            "name": "required|min:3",
            "email": "required|email",
            "opening_balance": "required|numeric",
        }

    def messages(self):
        return {
            "email.email": "Custom invalid email error",
        }


class UnauthorizedRequest(FormRequest):
    def authorize(self):
        return False

    def rules(self):
        return {"name": "required"}


class CustomerController(Controller):
    def store_autowired(self, form: CreateCustomerRequest):
        return Response.json({"status": "success", "data": form.validated()}, status=201)

    def store_unauthorized(self, form: UnauthorizedRequest):
        return Response.json({"status": "never_reached"})

    def store_manual(self):
        form = self.validate_request(CreateCustomerRequest)
        return Response.json({"status": "success", "data": form.validated()})


def make_test_environ(method="POST", path="/customers", data=None, headers=None):
    body = b""
    content_type = "application/x-www-form-urlencoded"
    if data:
        content_type = "application/json"
        body = json.dumps(data).encode("utf-8")

    env = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": sys.modules["io"].BytesIO(body),
        "HTTP_ACCEPT": "application/json",
    }
    if headers:
        for k, v in headers.items():
            env[f"HTTP_{k.upper().replace('-', '_')}"] = v
    return env


class TestFormRequest(PyFlowTestCase):

    def test_valid_form_request(self):
        env = make_test_environ(data={
            "name": "Abdur Rahim",
            "email": "rahim@example.com",
            "opening_balance": "1500.50",
            "extra_field": "injected_value",  # Should be stripped by validated()
        })
        req = Request(env)
        form = CreateCustomerRequest(req)
        form.validate()

        validated = form.validated()
        self.assertEqual(validated["name"], "Abdur Rahim")
        self.assertEqual(validated["email"], "rahim@example.com")
        self.assertEqual(validated["opening_balance"], "1500.50")
        self.assertNotIn("extra_field", validated)

    def test_invalid_form_request_raises_validation_exception(self):
        env = make_test_environ(data={
            "name": "Ab",  # min:3 fails
            "email": "not-an-email",  # email fails
            "opening_balance": "not-a-number",  # numeric fails
        })
        req = Request(env)
        form = CreateCustomerRequest(req)

        with self.assertRaises(ValidationException) as ctx:
            form.validate()

        errs = ctx.exception.errors
        self.assertIn("name", errs)
        self.assertIn("email", errs)
        self.assertIn("opening_balance", errs)
        self.assertEqual(errs["email"][0], "Custom invalid email error")

        resp = ctx.exception.response
        self.assertEqual(resp.status_code, 422)

    def test_unauthorized_form_request_raises_authorization_exception(self):
        env = make_test_environ(data={"name": "Alice"})
        req = Request(env)
        form = UnauthorizedRequest(req)

        with self.assertRaises(AuthorizationException):
            form.validate()

    def test_autowired_controller_action_success(self):
        env = make_test_environ(data={
            "name": "Sultana",
            "email": "sultana@example.com",
            "opening_balance": "250.0",
        })
        req = Request(env)
        session = Session()
        view_engine = None

        handler = action(CustomerController, "store_autowired")
        resp = handler(req, session, view_engine)

        self.assertEqual(resp.status_code, 201)
        body_str = resp.body if isinstance(resp.body, str) else resp.body.decode("utf-8")
        resp_data = json.loads(body_str)
        self.assertEqual(resp_data["status"], "success")
        self.assertEqual(resp_data["data"]["name"], "Sultana")

    def test_autowired_controller_action_validation_failure(self):
        env = make_test_environ(data={
            "name": "S",
            "email": "invalid",
        })
        req = Request(env)
        session = Session()
        view_engine = None

        handler = action(CustomerController, "store_autowired")
        resp = handler(req, session, view_engine)

        self.assertEqual(resp.status_code, 422)
        body_str = resp.body if isinstance(resp.body, str) else resp.body.decode("utf-8")
        resp_data = json.loads(body_str)
        self.assertIn("errors", resp_data)
        self.assertIn("name", resp_data["errors"])

    def test_autowired_controller_action_authorization_failure(self):
        env = make_test_environ(data={"name": "Sultana"})
        req = Request(env)
        session = Session()
        view_engine = None

        handler = action(CustomerController, "store_unauthorized")
        resp = handler(req, session, view_engine)

        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
