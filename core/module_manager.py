"""
core/module_manager.py
======================
মডিউল এবং প্লাগইন অটো-ডিসকভারি ও প্রোভাইডার লোডার।
"""

import os
import json
import importlib
from core.logger import Logger

class ModuleManager:
    def __init__(self, app):
        self.app = app
        self.modules = {}      # module_name -> manifest_dict
        self.plugins = {}      # plugin_name -> manifest_dict
        self.providers = []    # list of ServiceProvider instances

    def discover_and_load(self):
        """modules/ এবং plugins/ ডিরেক্টরি স্ক্যান করে সচল আইটেমগুলো লোড করে"""
        project_root = self.app.config.get("PROJECT_ROOT", os.getcwd())
        
        modules_dir = os.path.join(project_root, "modules")
        plugins_dir = os.path.join(project_root, "plugins")

        # ১. মডিউল স্ক্যানিং
        if os.path.exists(modules_dir):
            for item in os.listdir(modules_dir):
                item_path = os.path.join(modules_dir, item)
                if os.path.isdir(item_path):
                    manifest_path = os.path.join(item_path, "module.json")
                    if os.path.exists(manifest_path):
                        self._load_manifest(manifest_path, item, is_plugin=False)

        # ২. প্লাগইন স্ক্যানিং
        if os.path.exists(plugins_dir):
            for item in os.listdir(plugins_dir):
                item_path = os.path.join(plugins_dir, item)
                if os.path.isdir(item_path):
                    manifest_path = os.path.join(item_path, "plugin.json")
                    if os.path.exists(manifest_path):
                        self._load_manifest(manifest_path, item, is_plugin=True)

        Logger.info(f"Loaded {len(self.modules)} active modules, {len(self.plugins)} active plugins.")

    def _load_manifest(self, manifest_path: str, folder_name: str, is_plugin: bool):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            
            # enabled = true না থাকলে লোড করা হবে না
            if not manifest.get("enabled", False):
                return

            if is_plugin:
                self.plugins[folder_name] = manifest
            else:
                self.modules[folder_name] = manifest

            # প্রোভাইডার ক্লাসগুলো ডাইনামিকালি লোড ও ইনস্ট্যান্সিয়েট করি
            providers = manifest.get("providers", [])
            for provider_str in providers:
                provider_instance = self._instantiate_provider(provider_str)
                if provider_instance:
                    self.providers.append(provider_instance)
                    
        except Exception as e:
            Logger.error(f"Failed to load manifest {manifest_path}: {e}")

    def _instantiate_provider(self, provider_str: str):
        try:
            # e.g., "modules.inventory.providers.InventoryServiceProvider"
            module_path, class_name = provider_str.rsplit(".", 1)
            module = importlib.import_module(module_path)
            provider_class = getattr(module, class_name)
            return provider_class(self.app)
        except Exception as e:
            Logger.error(f"Failed to instantiate Service Provider {provider_str}: {e}")
            return None

    def register_providers(self):
        """সব সচল প্রোভাইডারের register() মেথড রান করে"""
        for provider in self.providers:
            try:
                provider.register()
            except Exception as e:
                Logger.error(f"Error registering provider {provider.__class__.__name__}: {e}")

    def boot_providers(self):
        """সব সচল প্রোভাইডারের boot() মেথড রান করে"""
        for provider in self.providers:
            try:
                provider.boot()
            except Exception as e:
                Logger.error(f"Error booting provider {provider.__class__.__name__}: {e}")
