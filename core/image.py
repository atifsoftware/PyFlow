"""
core/image.py
=============
Image Processing & Upload Helper Library (Pillow-based)
Replicates and enhances PHP's ImageProcessor.php and ImageHandler.php.
Supports resize, center crop, size/mime validation, and mandatory WebP conversion.
"""

import os
import uuid
from io import BytesIO
from PIL import Image
from core.request import UploadedFile


class ImageProcessor:
    def __init__(self, file_source=None):
        """
        :param file_source: core.request.UploadedFile অবজেক্ট অথবা ফাইলের লোকাল পাথ
        """
        self.image = None
        self.width = 0
        self.height = 0
        self.quality = 80
        
        if file_source:
            self.load(file_source)

    def load(self, file_source):
        """
        লোকাল ফাইল পাথ বা আপলোড করা ফাইল লোড করে।
        """
        try:
            if isinstance(file_source, UploadedFile):
                # Request-এ মেমরি ডাটা থেকে সরাসরি Pillow ইমেজ তৈরি
                self.image = Image.open(BytesIO(file_source.read()))
            elif isinstance(file_source, str):
                if os.path.exists(file_source):
                    self.image = Image.open(file_source)
                else:
                    return self
            else:
                return self
                
            if self.image:
                # Transparency ঠিক রাখার জন্য RGB তে কনভার্ট করা (যেমন PNG বা GIF-এর জন্য)
                if self.image.mode in ('RGBA', 'LA') or (self.image.mode == 'P' and 'transparency' in self.image.info):
                    self.image = self.image.convert('RGBA')
                else:
                    self.image = self.image.convert('RGB')
                    
                self.width, self.height = self.image.size
        except Exception as e:
            self.image = None
            raise ValueError(f"ইমেজ লোড করতে ব্যর্থ: {e}")

        return self

    def resize(self, max_width: int, max_height: int):
        """
        অ্যাসপেক্ট রেশিও ঠিক রেখে ইমেজ রিসাইজ করে (অতিরিক্ত বড় বা ছোট করা রোধ করে)।
        """
        if not self.image:
            return self

        # অ্যাসপেক্ট রেশিও হিসাব
        ratio = min(max_width / self.width, max_height / self.height)
        
        # ইমেজ অলরেডি ছোট হলে রিসাইজ করার দরকার নেই (upscaling এড়াতে)
        if ratio >= 1.0:
            return self

        new_width = int(self.width * ratio)
        new_height = int(self.height * ratio)
        
        self.image = self.image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        self.width, self.height = self.image.size
        return self

    def crop_center(self, target_width: int, target_height: int):
        """
        ইমেজের একদম মাঝখান থেকে নির্দিষ্ট উইডথ এবং হাইট অনুযায়ী ক্রপ করে।
        থাম্বনেইল বা প্রোডাক্ট ব্যানারের জন্য উপযোগী।
        """
        if not self.image:
            return self

        original_aspect = self.width / self.height
        target_aspect = target_width / target_height

        if original_aspect > target_aspect:
            # ইমেজটি চওড়া, তাই দুই পাশ থেকে কাটতে হবে
            new_height = self.height
            new_width = int(self.height * target_aspect)
            left = (self.width - new_width) / 2
            top = 0
            right = left + new_width
            bottom = new_height
        else:
            # ইমেজটি লম্বা, তাই উপর-নিচ থেকে কাটতে হবে
            new_width = self.width
            new_height = int(self.width / target_aspect)
            left = 0
            top = (self.height - new_height) / 2
            right = new_width
            bottom = top + new_height

        # ক্রপ করার পর নির্দিষ্ট টার্গেট সাইজে রিসাইজ করা
        self.image = self.image.crop((left, top, right, bottom))
        self.image = self.image.resize((target_width, target_height), Image.Resampling.LANCZOS)
        self.width, self.height = self.image.size
        return self

    def set_quality(self, quality: int):
        """WebP কোয়ালিটি সেট করা (১ থেকে ১০০)"""
        self.quality = max(1, min(100, quality))
        return self

    def save_as_webp(self, subfolder: str = "products", filename: str = None) -> str:
        """
        ইমেজটি WebP ফরম্যাটে কনভার্ট করে public/uploads/{subfolder} এ সেভ করে।
        ডাটাবেসে সেভ করার জন্য রিলেটিভ পাথ রিটার্ন করে (যেমন: uploads/products/xyz.webp)।
        """
        if not self.image:
            return ""

        physical_dir = f"public/uploads/{subfolder}"
        os.makedirs(physical_dir, exist_ok=True)

        if not filename:
            filename = f"{subfolder}_{uuid.uuid4().hex}.webp"
        elif not filename.lower().endswith(".webp"):
            filename = f"{os.path.splitext(filename)[0]}.webp"

        full_destination = os.path.join(physical_dir, filename)
        db_path = f"uploads/{subfolder}/{filename}"

        try:
            # WebP ফরম্যাটে ইমেজ সেভ করা
            if self.image.mode == 'RGBA':
                # ট্রান্সপারেন্ট সহ WebP সেভ
                self.image.save(full_destination, "WEBP", quality=self.quality, lossless=False)
            else:
                self.image.save(full_destination, "WEBP", quality=self.quality)
            return db_path
        except Exception as e:
            raise IOError(f"WebP সেভ করতে সমস্যা হয়েছে: {e}")

    @staticmethod
    def upload(uploaded_file: UploadedFile, folder: str = "products", max_width: int = 800, max_height: int = 800, quality: int = 80) -> dict:
        """
        সহজ ফাইল আপলোড হেল্পার (PHP ImageHandler.php এর মতো ভ্যালিডেশন সহ)।
        """
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif']
        max_size = 5 * 1024 * 1024 # 5MB

        # সাইজ ভ্যালিডেশন
        if uploaded_file.size > max_size:
            return {"success": False, "message": "ফাইলটি অনেক বড় (সর্বোচ্চ 5MB অনুমোদিত)"}

        # টাইপ ভ্যালিডেশন
        if uploaded_file.content_type not in allowed_types:
            return {"success": False, "message": "ভুল ফাইল টাইপ। শুধুমাত্র JPG, PNG, WebP এবং GIF অনুমোদিত।"}

        try:
            processor = ImageProcessor(uploaded_file)
            processor.resize(max_width, max_height)
            processor.set_quality(quality)
            db_path = processor.save_as_webp(folder)
            
            if db_path:
                return {
                    "success": True,
                    "path": db_path,
                    "url": f"/static/{folder}/{os.path.basename(db_path)}"
                }
        except Exception as e:
            return {"success": False, "message": f"ফাইল আপলোড ব্যর্থ হয়েছে: {str(e)}"}

        return {"success": False, "message": "ফাইল প্রসেস করা যায়নি"}
