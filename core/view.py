"""
core/view.py
============
হালকা-পাতলা কাস্টম টেমপ্লেট ইঞ্জিন (Blade/Jinja স্টাইল, কিন্তু নিজে লেখা):

  {{ variable }}         -> auto HTML-escaped আউটপুট (XSS প্রতিরোধ)
  {!! raw_html !!}       -> escape ছাড়া raw আউটপুট (নিজে দায়িত্ব নিয়ে ব্যবহার করবেন)
  @if(condition) ... @elif(cond) ... @else ... @endif
  @foreach(item in items) ... @endforeach
  @extends('layout.master')
  @section('content') ... @endsection
  @yield('content')
  @include('partials.header')
  @csrf   -> hidden CSRF input ফিল্ড বসিয়ে দেয়

টেমপ্লেট compile করে পাইথন কোডে রূপান্তর করা হয়, কিন্তু eval করা হয় একটা
রেসট্রিক্টেড namespace-এ যেখানে শুধু পাস করা ভ্যারিয়েবল আর সীমিত builtin থাকে।
"""

import re
import os
from core.security import e as escape_html


class ViewError(Exception):
    pass


class TemplateEngine:
    def __init__(self, views_dir="app/views", cache_enabled=False):
        self.views_dir = views_dir
        self.cache_enabled = cache_enabled
        self._compiled_cache = {}

    def render(self, template_name: str, data: dict = None) -> str:
        data = data or {}
        source = self._read_template(template_name)
        source = self._resolve_extends(source, data)
        html_out = self._compile_and_run(source, data)
        return html_out

    # ---------------------------------------------------------------- loading
    def _template_path(self, name: str) -> str:
        name = name.replace(".", "/") + ".html"
        path = os.path.join(self.views_dir, name)
        real_views = os.path.realpath(self.views_dir)
        real_path = os.path.realpath(path)
        if not real_path.startswith(real_views):
            raise ViewError("অবৈধ টেমপ্লেট পাথ")
        if not os.path.exists(real_path):
            raise ViewError(f"টেমপ্লেট পাওয়া যায়নি: {name}")
        return real_path

    def _read_template(self, name: str) -> str:
        with open(self._template_path(name), "r", encoding="utf-8") as f:
            return f.read()

    # -------------------------------------------------------------- @extends
    def _resolve_extends(self, source: str, data: dict) -> str:
        m = re.search(r"@extends\(['\"]([\w./]+)['\"]\)", source)
        if not m:
            return source

        layout_name = m.group(1)
        child_source = re.sub(r"@extends\(['\"][\w./]+['\"]\)", "", source)

        sections = {}
        section_pattern = re.compile(
            r"@section\(['\"](\w+)['\"]\)(.*?)@endsection", re.DOTALL
        )
        for sec_match in section_pattern.finditer(child_source):
            sections[sec_match.group(1)] = sec_match.group(2)

        layout_source = self._read_template(layout_name)
        layout_source = self._resolve_extends(layout_source, data)  # nested layout সাপোর্ট

        def yield_replace(ym):
            section_name = ym.group(1)
            return sections.get(section_name, "")

        return re.sub(r"@yield\(['\"](\w+)['\"]\)", yield_replace, layout_source)

    # -------------------------------------------------------------- @include
    def _resolve_includes(self, source: str, data: dict) -> str:
        def include_replace(m):
            included = self._read_template(m.group(1))
            included = self._resolve_includes(included, data)
            return included

        return re.sub(r"@include\(['\"]([\w./]+)['\"]\)", include_replace, source)

    # --------------------------------------------------------------- compile
    def _compile_and_run(self, source: str, data: dict) -> str:
        source = self._resolve_includes(source, data)

        # @csrf -> hidden input (data-এ 'csrf_token' পাস করা থাকবে কন্ট্রোলার থেকে)
        source = source.replace(
            "@csrf",
            '<input type="hidden" name="_token" value="{{ csrf_token }}">',
        )

        lines = ["def __render__(ctx):", "    __out = []", "    __append = __out.append"]
        lines.append("    __locals = ctx")

        # লাইন বাই লাইন টোকেনাইজ - {{ }}, {!! !!}, @if/@foreach ইত্যাদি
        pos = 0
        pattern = re.compile(
            r"(\{\{.*?\}\}|\{!!.*?!!\}|@if\(.*?\)|@elif\(.*?\)|@else|@endif"
            r"|@foreach\(.*?\)|@endforeach)",
            re.DOTALL,
        )
        indent = 1

        def emit_text(text):
            if text:
                lines.append("    " * indent + f"__append({text!r})")

        last_end = 0
        for m in pattern.finditer(source):
            emit_text(source[last_end:m.start()])
            token = m.group(0)

            if token.startswith("{{"):
                expr = token[2:-2].strip()
                lines.append("    " * indent + f"__append(__escape(__eval({expr!r}, __locals)))")
            elif token.startswith("{!!"):
                expr = token[3:-3].strip()
                lines.append("    " * indent + f"__append(str(__eval({expr!r}, __locals)))")
            elif token.startswith("@if("):
                cond = token[4:-1]
                lines.append("    " * indent + f"if __eval({cond!r}, __locals):")
                indent += 1
            elif token.startswith("@elif("):
                cond = token[6:-1]
                indent -= 1
                lines.append("    " * indent + f"elif __eval({cond!r}, __locals):")
                indent += 1
            elif token == "@else":
                indent -= 1
                lines.append("    " * indent + "else:")
                indent += 1
            elif token == "@endif":
                indent -= 1
            elif token.startswith("@foreach("):
                inner = token[9:-1]  # "item in items"
                var_name, _, iterable_expr = inner.partition(" in ")
                var_name = var_name.strip()
                lines.append(
                    "    " * indent
                    + f"for {var_name} in __eval({iterable_expr.strip()!r}, __locals):"
                )
                lines.append("    " * (indent + 1) + f"__locals = dict(__locals); __locals[{var_name!r}] = {var_name}")
                indent += 1
            elif token == "@endforeach":
                indent -= 1

            last_end = m.end()

        emit_text(source[last_end:])
        lines.append("    " * 1 + "return ''.join(__out)")

        code = "\n".join(lines)

        safe_globals = {
            "__builtins__": {
                "len": len, "str": str, "int": int, "float": float,
                "range": range, "enumerate": enumerate, "bool": bool,
                "list": list, "dict": dict,
            },
            "__escape": escape_html,
            "__eval": self._safe_eval,
        }
        local_ns = {}
        try:
            exec(code, safe_globals, local_ns)
            return local_ns["__render__"](data)
        except Exception as exc:
            raise ViewError(f"টেমপ্লেট রেন্ডার করতে সমস্যা হয়েছে: {exc}") from exc

    @staticmethod
    def _safe_eval(expr: str, context: dict):
        """
        টেমপ্লেট এক্সপ্রেশন eval করে সীমিত namespace-এ - শুধু context-এর
        ভ্যারিয়েবল আর কিছু নিরাপদ builtin অ্যাক্সেস করা যায়, os/import ইত্যাদি নয়।
        """
        safe_builtins = {"len": len, "str": str, "int": int, "float": float, "bool": bool}
        try:
            return eval(expr, {"__builtins__": safe_builtins}, context)
        except Exception:
            return ""
