"""
core/view.py
============
Jinja2 Template Engine Integration

Features:
  - Auto HTML escaping (XSS protection)
  - Template inheritance (@extends → {% extends %})
  - Sections (@section/@yield → {% block %})
  - Includes (@include → {% include %})
  - CSRF token support
  - Multi-namespace support (e.g., inventory::views)
  - Component support (@component)

Migration from custom engine:
  {{ variable }}         → {{ variable }} (same, auto-escaped)
  {!! raw_html !!}       → {{ variable|safe }}
  @if(condition)         → {% if condition %}
  @foreach(item in items)→ {% for item in items %}
  @extends('layout')     → {% extends 'layout.html' %}
  @section('name')       → {% block name %}
  @yield('name')         → {% block name %}{% endblock %}
  @include('partial')    → {% include 'partial.html' %}
  @csrf                  → <input type="hidden" name="_token" value="{{ csrf_token }}">
"""

import os
from jinja2 import Environment, FileSystemLoader, ChoiceLoader, PrefixLoader, TemplateNotFound
from core.security import e as escape_html


class ViewError(Exception):
    pass


class TemplateEngine:
    def __init__(self, views_dir="app/views", cache_enabled=False):
        self.views_dir = views_dir
        self.cache_enabled = cache_enabled
        self.namespaces = {}
        
        # Setup Jinja2 environment with security features
        loader = FileSystemLoader(views_dir)
        self.env = Environment(
            loader=loader,
            autoescape=True,  # Auto HTML escaping for XSS protection
            cache_size=400 if cache_enabled else 0,  # Cache templates in production
            trim_blocks=True,
            lstrip_blocks=True,
        )
        
        # Add custom filters
        self.env.filters['escape'] = escape_html
        self.env.globals['e'] = escape_html
        
    def register_namespace(self, name: str, views_dir: str):
        """Register view namespace (e.g., inventory::views)"""
        self.namespaces[name] = views_dir
        # Update loader to include namespaces
        loaders = {
            '': FileSystemLoader(self.views_dir)
        }
        for ns_name, ns_dir in self.namespaces.items():
            loaders[ns_name] = FileSystemLoader(ns_dir)
        
        self.env.loader = ChoiceLoader([PrefixLoader(loaders)])

    def render(self, template_name: str, data: dict = None) -> str:
        """Render template with given data"""
        data = data or {}
        
        # Convert dot notation to path (e.g., home.index → home/index.html)
        template_path = template_name.replace(".", "/") + ".html"
        
        # Handle namespace notation (e.g., inventory::home.index)
        if "::" in template_path:
            ns, template_path = template_path.split("::", 1)
            template_path = f"{ns}:{template_path}"
        
        try:
            template = self.env.get_template(template_path)
            return template.render(**data)
        except TemplateNotFound as e:
            raise ViewError(f"Template not found: {template_name}") from e
        except Exception as e:
            raise ViewError(f"Error rendering template {template_name}: {e}") from e

    def _read_template(self, name: str) -> str:
        """Read raw template source (for backward compatibility)"""
        path = self._template_path(name)
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def _template_path(self, name: str) -> str:
        """Get absolute template path with security checks"""
        if "::" in name:
            ns, template_name = name.split("::", 1)
            if ns in self.namespaces:
                views_dir = self.namespaces[ns]
                template_file = template_name.replace(".", "/") + ".html"
                path = os.path.abspath(os.path.join(views_dir, template_file))
                real_views = os.path.realpath(views_dir)
                real_path = os.path.realpath(path)
                if not real_path.startswith(real_views):
                    raise ViewError("Invalid template path")
                if not os.path.exists(real_path):
                    raise ViewError(f"Template not found: {name} in namespace {ns}")
                return real_path
            else:
                raise ViewError(f"Unknown view namespace: {ns}")

        name = name.replace(".", "/") + ".html"
        path = os.path.join(self.views_dir, name)
        real_views = os.path.realpath(self.views_dir)
        real_path = os.path.realpath(path)
        if not real_path.startswith(real_views):
            raise ViewError("Invalid template path")
        if not os.path.exists(real_path):
            raise ViewError(f"Template not found: {name}")
        return real_path
