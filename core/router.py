"""
core/router.py
===============
একটা ছোট কিন্তু শক্তিশালী Router:
- GET/POST/PUT/PATCH/DELETE সাপোর্ট
- Dynamic segment: /users/{id}  অথবা টাইপ সহ /users/{id:int}
- Named routes (url_for দিয়ে URL জেনারেট করা যায়)
- Middleware আলাদাভাবে বা group করে লাগানো যায়
- 404 / 405 handling
"""

import re


class Route:
    def __init__(self, method, pattern, handler, name=None, middleware=None):
        self.method = method.upper()
        self.raw_pattern = pattern
        self.handler = handler
        self.name = name
        self.middleware = middleware or []
        self.regex, self.param_names = self._compile(pattern)

    @staticmethod
    def _compile(pattern: str):
        param_names = []
        type_map = {
            "int": r"(?P<{name}>\d+)",
            "str": r"(?P<{name}>[^/]+)",
            "slug": r"(?P<{name}>[a-zA-Z0-9\-_]+)",
        }

        def replace(match):
            raw = match.group(1)
            if ":" in raw:
                name, typ = raw.split(":", 1)
            else:
                name, typ = raw, "str"
            param_names.append((name, typ))  # (name, type) tuple
            tpl = type_map.get(typ, type_map["str"])
            return tpl.format(name=name)

        regex_str = re.sub(r"\{([^}]+)\}", replace, pattern)
        regex_str = f"^{regex_str}/?$"
        return re.compile(regex_str), param_names

    def match(self, path):
        m = self.regex.match(path)
        if not m:
            return None
        raw_params = m.groupdict()
        # int param গুলো cast করা
        result = {}
        for name, typ in self.param_names:
            val = raw_params.get(name)
            if val is not None and typ == "int":
                try:
                    val = int(val)
                except (ValueError, TypeError):
                    pass
            result[name] = val
        return result

    def url(self, **kwargs) -> str:
        url = self.raw_pattern
        for key, value in kwargs.items():
            url = re.sub(r"\{" + key + r"(:\w+)?\}", str(value), url)
        return url


class _RouteGroup:
    """
    with router.group(prefix="/admin", middleware=[auth_middleware]):
        router.get("/dashboard", ...)
    """

    def __init__(self, outer, prefix="", middleware=None):
        self.outer = outer
        self.prefix = prefix
        self.middleware = middleware or []

    def __enter__(self):
        self._old_prefix = self.outer._group_prefix
        self._old_mw = self.outer._group_middleware
        self.outer._group_prefix = self._old_prefix + self.prefix
        self.outer._group_middleware = self._old_mw + self.middleware
        return self.outer

    def __exit__(self, *exc):
        self.outer._group_prefix = self._old_prefix
        self.outer._group_middleware = self._old_mw


class Router:
    def __init__(self):
        self.routes = []
        self._group_prefix = ""
        self._group_middleware = []
        self._names = {}

    # ------------------------------------------------------------ registration
    def _add(self, method, pattern, handler, name=None, middleware=None):
        full_pattern = self._group_prefix + pattern
        full_middleware = self._group_middleware + (middleware or [])
        route = Route(method, full_pattern, handler, name, full_middleware)
        self.routes.append(route)
        if name:
            self._names[name] = route
        return route

    def get(self, pattern, handler, name=None, middleware=None):
        return self._add("GET", pattern, handler, name, middleware)

    def post(self, pattern, handler, name=None, middleware=None):
        return self._add("POST", pattern, handler, name, middleware)

    def put(self, pattern, handler, name=None, middleware=None):
        return self._add("PUT", pattern, handler, name, middleware)

    def patch(self, pattern, handler, name=None, middleware=None):
        return self._add("PATCH", pattern, handler, name, middleware)

    def delete(self, pattern, handler, name=None, middleware=None):
        return self._add("DELETE", pattern, handler, name, middleware)

    def websocket(self, pattern, handler, name=None, middleware=None):
        return self._add("WEBSOCKET", pattern, handler, name, middleware)

    def resource(self, base_path, controller_cls, name=None, middleware=None):
        """
        RESTful resource route একসাথে বানিয়ে দেয় (index/show/create/store/edit/update/destroy)
        controller_cls একটা Controller সাবক্লাস হতে হবে (instance না) - প্রতিটা
        রিকোয়েস্টে নতুন instance বানিয়ে core.controller.action() দিয়ে বাইন্ড করা হয়।
        """
        from core.controller import action

        n = name or base_path.strip("/")
        self.get(base_path, action(controller_cls, "index"), name=f"{n}.index", middleware=middleware)
        self.get(f"{base_path}/create", action(controller_cls, "create"), name=f"{n}.create", middleware=middleware)
        self.post(base_path, action(controller_cls, "store"), name=f"{n}.store", middleware=middleware)
        self.get(f"{base_path}/{{id:int}}", action(controller_cls, "show"), name=f"{n}.show", middleware=middleware)
        self.get(f"{base_path}/{{id:int}}/edit", action(controller_cls, "edit"), name=f"{n}.edit", middleware=middleware)
        self.put(f"{base_path}/{{id:int}}", action(controller_cls, "update"), name=f"{n}.update", middleware=middleware)
        self.delete(f"{base_path}/{{id:int}}", action(controller_cls, "destroy"), name=f"{n}.destroy", middleware=middleware)

    def group(self, prefix="", middleware=None):
        return _RouteGroup(self, prefix, middleware)

    # ------------------------------------------------------------- dispatch
    def resolve(self, method, path):
        """
        ম্যাচ করা route রিটার্ন করে + params। কোনো path ম্যাচ করলেও method না
        মিললে 405 বোঝানোর জন্য matched_any_path=True রিটার্ন করে।
        """
        matched_any_path = False
        for route in self.routes:
            params = route.match(path)
            if params is not None:
                matched_any_path = True
                if route.method == method.upper():
                    return route, params
        if matched_any_path:
            return "METHOD_NOT_ALLOWED", None
        return None, None

    def url_for(self, name, **kwargs) -> str:
        route = self._names.get(name)
        if not route:
            raise ValueError(f"'{name}' নামে কোনো route পাওয়া যায়নি")
        return route.url(**kwargs)
