"""
core/container.py
=================
Dependency Injection Container (IoC Container).
"""

import inspect
from core.logger import Logger

class Container:
    def __init__(self):
        self._bindings = {}
        self._instances = {}

    def bind(self, abstract, concrete=None, singleton=False):
        """সিঙ্গেলটন বা ফ্যাক্টরি বাইন্ডিং করা"""
        if concrete is None:
            concrete = abstract
        self._bindings[abstract] = (concrete, singleton)

    def singleton(self, abstract, concrete=None):
        """সিঙ্গেলটন হিসেবে বাইন্ড করা"""
        self.bind(abstract, concrete, singleton=True)

    def instance(self, abstract, instance_obj):
        """নির্দিষ্ট অবজেক্ট সরাসরি রেজিস্ট্রেশন করা"""
        self._instances[abstract] = instance_obj

    def resolve(self, abstract):
        """ক্লাস টাইপ বা রেজিস্টার্ড কি ধরে ডিপেন্ডেন্সি রিজলভ করে"""
        # ১. যদি সরাসরি ইনস্ট্যান্স রেজিস্টার্ড থাকে
        if abstract in self._instances:
            return self._instances[abstract]

        # ২. যদি কোনো বাইন্ডিং থাকে
        if abstract in self._bindings:
            concrete, singleton = self._bindings[abstract]
            if callable(concrete) and not inspect.isclass(concrete):
                # এটি একটি ফ্যাক্টরি ফাংশন
                resolved = concrete(self)
            else:
                # এটি একটি ক্লাস টাইপ
                resolved = self.autowire(concrete)
            
            if singleton:
                self._instances[abstract] = resolved
            return resolved

        # ৩. বাইন্ডিং না থাকলে অটো-ওয়্যারিং এর চেষ্টা করি
        if inspect.isclass(abstract):
            return self.autowire(abstract)

        raise Exception(f"Unable to resolve dependency: {abstract}")

    def autowire(self, cls):
        """ইন্সপেকশন ব্যবহার করে স্বয়ংক্রিয়ভাবে ক্লাসের ডিপেন্ডেন্সি ইনজেক্ট করে"""
        if not hasattr(cls, "__init__") or cls.__init__ is object.__init__:
            return cls()

        sign = inspect.signature(cls.__init__)
        params = list(sign.parameters.values())[1:]  # self বাদ দিয়ে

        dependencies = []
        for param in params:
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                # টাইপ হিন্ট না থাকলে যদি প্যারামিটারের ডিফল্ট ভ্যালু থাকে
                if param.default is not inspect.Parameter.empty:
                    dependencies.append(param.default)
                else:
                    raise Exception(
                        f"Cannot autowire parameter '{param.name}' in class '{cls.__name__}': missing type annotation or default value."
                    )
            else:
                # টাইপ হিন্ট থাকলে সেটি রিজলভ করি
                dependencies.append(self.resolve(annotation))

        return cls(*dependencies)
