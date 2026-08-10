#!/usr/bin/env python
"""
Template Migration Script: Custom Blade-like → Jinja2
Converts all template files from old custom syntax to Jinja2 syntax
"""
import os
import re

def convert_template(filepath):
    """Convert a single template file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    # 1. @extends('layout.master') → {% extends 'layout/master.html' %}
    content = re.sub(
        r"@extends\(['\"]([^'\"]+)['\"]\)",
        lambda m: "{% extends '" + m.group(1).replace('.', '/') + ".html' %}",
        content
    )
    
    # 2. @section('name') → {% block name %}
    content = re.sub(
        r"@section\(['\"](\w+)['\"]\)",
        lambda m: "{% block " + m.group(1) + " %}",
        content
    )
    
    # 3. @endsection → {% endblock %}
    content = re.sub(r"@endsection", "{% endblock %}", content)
    
    # 4. @yield('name') → {% block name %}{% endblock %} (for parent templates)
    # Actually in Jinja2, @yield should just be {% block name %}{% endblock %}
    # But since we're using child templates, @yield in parent = {% block name %}{% endblock %}
    content = re.sub(
        r"@yield\(['\"](\w+)['\"]\)",
        lambda m: "{% block " + m.group(1) + " %}{% endblock %}",
        content
    )
    
    # 5. @if(condition) → {% if condition %}
    content = re.sub(r"@if\((.*?)\)", r"{% if \1 %}", content)
    
    # 6. @elif(condition) → {% elif condition %}
    content = re.sub(r"@elif\((.*?)\)", r"{% elif \1 %}", content)
    
    # 7. @else → {% else %}
    content = re.sub(r"@else(?!\w)", "{% else %}", content)
    
    # 8. @endif → {% endif %}
    content = re.sub(r"@endif", "{% endif %}", content)
    
    # 9. @foreach(item in items) → {% for item in items %}
    content = re.sub(r"@foreach\((.*?)\)", r"{% for \1 %}", content)
    
    # 10. @endforeach → {% endfor %}
    content = re.sub(r"@endforeach", "{% endfor %}", content)
    
    # 11. @include('partial.name') → {% include 'partial/name.html' %}
    content = re.sub(
        r"@include\(['\"]([^'\"]+)['\"]\)",
        lambda m: "{% include '" + m.group(1).replace('.', '/') + ".html' %}",
        content
    )
    
    # 12. @csrf → <input type="hidden" name="_token" value="{{ csrf_token }}">
    content = re.sub(
        r"@csrf",
        '<input type="hidden" name="_token" value="{{ csrf_token }}">',
        content
    )
    
    # 13. {!! raw_html !!} → {{ variable|safe }} (keep the expression but add |safe filter)
    content = re.sub(r"{!!\s*(.*?)\s*!!}", r"{{ \1|safe }}", content)
    
    # Write back if changed
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    views_dir = 'app/views'
    converted = 0
    skipped = 0
    
    for root, dirs, files in os.walk(views_dir):
        for file in files:
            if file.endswith('.html'):
                filepath = os.path.join(root, file)
                try:
                    if convert_template(filepath):
                        print(f"✓ Converted: {filepath}")
                        converted += 1
                    else:
                        skipped += 1
                except Exception as e:
                    print(f"✗ Error converting {filepath}: {e}")
    
    print(f"\n{'='*50}")
    print(f"Migration Complete!")
    print(f"Converted: {converted} files")
    print(f"Skipped (no changes): {skipped} files")

if __name__ == '__main__':
    main()
