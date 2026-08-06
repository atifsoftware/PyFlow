"""
tests/test_circular_dependency.py
==================================
Tests the import integrity and circular dependencies across all project modules.
"""

import unittest
import os
import sys
import importlib


class CircularDependencyTest(unittest.TestCase):
    def test_import_integrity(self):
        """Scans core and app packages to verify all modules can be imported without errors."""
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

        modules_to_test = []
        for base_dir in ["core", "app"]:
            full_path = os.path.join(root_dir, base_dir)
            if not os.path.exists(full_path):
                continue
            for root, dirs, files in os.walk(full_path):
                for file in files:
                    if file.endswith(".py") and file != "__init__.py":
                        # Convert filepath to module name
                        rel_path = os.path.relpath(os.path.join(root, file), root_dir)
                        module_name = rel_path.replace(os.sep, ".").replace(".py", "")
                        modules_to_test.append(module_name)

        # Attempt importing each module
        for mod in modules_to_test:
            try:
                importlib.import_module(mod)
            except Exception as e:
                self.fail(f"Circular dependency or import failure detected in '{mod}': {e}")


if __name__ == "__main__":
    unittest.main()
