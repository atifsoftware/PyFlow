"""
core/provider.py
=================
Service Provider-এর বেস ক্লাস। প্রতিটি মডিউল এবং প্লাগইন নিজস্ব সার্ভিস প্রোভাইডার
তৈরি করে এই ক্লাসকে ইনহেরিট করবে।
"""

class ServiceProvider:
    def __init__(self, app):
        """
        :param app: Application ইনস্ট্যান্স (core.application.Application)
        """
        self.app = app

    def register(self):
        """
        মডিউলের কনটেইনার বাইন্ডিং বা ব্যাকগ্রাউন্ড সার্ভিস রেজিস্টার করার জন্য।
        (বুট প্রসেসের শুরুতে রান করে)
        """
        pass

    def boot(self):
        """
        মডিউলের রাউট, ভিউ নেমস্পেস, ক্যাশ, বা লিসেনার বুট করার জন্য।
        (সব সার্ভিস রেজিস্টার হওয়ার পর রান করে)
        """
        pass
