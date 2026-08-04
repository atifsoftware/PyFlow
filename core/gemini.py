"""
core/gemini.py
==============
Google Gemini AI Helper Library
Handles communication with Google Gemini Flash API (equivalent to PHP Gemini.php).
Uses pure Python stdlib (urllib.request) to keep it dependency-free and lightweight.
"""

import json
import urllib.request
import urllib.error
import logging

logger = logging.getLogger("pymvc.gemini")


class Gemini:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Gemini 2.0 Flash API endpoint
        self.api_url = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent"

    def generate_response(self, prompt: str, system_instruction: str = "") -> str:
        """
        Gemini API-তে প্রম্পট পাঠিয়ে টেক্সট রেসপন্স রিটার্ন করে।
        
        :param prompt: ইউজারের প্রম্পট স্ট্রিং
        :param system_instruction: জেমিনির জন্য নির্দেশিকা (optional)
        :return: জেমিনির দেওয়া টেক্সট রেসপন্স অথবা এরর মেসেজ
        """
        if not self.api_key:
            return "Error: API Key is missing. Please set GEMINI_API_KEY in .env file."

        url = f"{self.api_url}?key={self.api_key}"

        # JSON Payload তৈরি (PHP structure-এর সাথে হুবহু মিল রেখে)
        data = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 1024,
            }
        }

        # System Instruction থাকলে তা পে-লোডে যোগ করা
        if system_instruction:
            data["system_instruction"] = {
                "parts": [
                    {"text": system_instruction}
                ]
            }

        headers = {
            "Content-Type": "application/json"
        }

        req_body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                status_code = response.getcode()
                res_body = response.read().decode("utf-8")
                
                if status_code != 200:
                    return f"API Error: Server returned status {status_code}"

                result = json.loads(res_body)
                
                # Response থেকে টেক্সট বের করা
                try:
                    text_out = result['candidates'][0]['content']['parts'][0]['text']
                    return text_out
                except (KeyError, IndexError):
                    return "Error: Could not parse AI response structure."

        except urllib.error.HTTPError as e:
            try:
                err_content = e.read().decode("utf-8")
                err_json = json.loads(err_content)
                err_msg = err_json.get("error", {}).get("message", "Unknown API error")
                return f"API Error ({e.code}): {err_msg}"
            except Exception:
                return f"API HTTP Error ({e.code}): {e.reason}"
        except urllib.error.URLError as e:
            return f"Connection Error: {e.reason}"
        except Exception as e:
            logger.error("Gemini invocation failed: %s", e)
            return f"Unexpected Error: {str(e)}"
