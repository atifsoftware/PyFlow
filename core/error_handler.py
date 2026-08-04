"""
core/error_handler.py
======================
Enhanced Intelligent Error Handler & Suggestion System
Detects syntax errors, name errors, attribute errors, and provides solutions
using Levenshtein similarity variable/method name suggestions.
Replicates and adapts PHP's IntelligentErrorHandler.php.
"""

import sys
import os
import re
import traceback
import urllib.parse
import inspect


class IntelligentErrorHandler:
    @staticmethod
    def get_levenshtein_distance(s1: str, s2: str) -> int:
        """দুটি স্ট্রিংয়ের মধ্যকার Levenshtein দূরত্ব নির্ণয় করে"""
        if len(s1) > len(s2):
            s1, s2 = s2, s1

        distances = range(len(s1) + 1)
        for i2, c2 in enumerate(s2):
            distances_ = [i2+1]
            for i1, c1 in enumerate(s1):
                if c1 == c2:
                    distances_.append(distances[i1])
                else:
                    distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
            distances = distances_
        return distances[-1]

    @classmethod
    def find_similar_names(cls, target: str, candidates: list, max_distance: int = 2) -> list:
        """টার্গেট বানানের সাথে কাছাকাছি থাকা অন্যান্য সঠিক নামের সাজেশন দেয়"""
        similar = []
        for cand in candidates:
            if cand.startswith("_"):
                continue
            dist = cls.get_levenshtein_distance(target, cand)
            if 0 < dist <= max_distance:
                similar.append(cand)
        return similar

    @classmethod
    def get_code_context(cls, filepath: str, error_line: int, context_range: int = 4) -> str:
        """ভুলের লাইনের আশেপাশের কোড রিড করে Pointer (>>>) সহ স্ট্রিং রিটার্ন করে"""
        if not os.path.exists(filepath):
            return ""
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return ""

        total_lines = len(lines)
        start = max(0, error_line - context_range - 1)
        end = min(total_lines, error_line + context_range)

        context = []
        for i in range(start, end):
            line_no = i + 1
            marker = " >>> " if line_no == error_line else "     "
            # tabs HTML-এ ভাঙা রোধ করার জন্য স্পেস দিয়ে রিপ্লেস করা
            line_content = lines[i].replace("\t", "    ").rstrip()
            context.append(f"{marker}{line_no:4d} | {line_content}")

        return "\n".join(context)

    @classmethod
    def analyze_exception(cls, exc: Exception) -> dict:
        """
        Exception টি এনালাইসিস করে ভেরিয়েবল/মেথড ভুল টাইপ হয়েছে কিনা খুজে বের করে।
        """
        analysis = {
            "category": "runtime",
            "possible_causes": [],
            "suggestion": ""
        }
        
        exc_type = type(exc).__name__
        exc_msg = str(exc)

        # NameError (ভেরিয়েবল টাইপো)
        if exc_type == "NameError":
            analysis["category"] = "name_error"
            analysis["possible_causes"] = [
                "ভেরিয়েবলটি ঘোষণা করা হয়নি",
                "ভেরিয়েবল বানানে ভুল (Typo)",
                "ভুল স্কোপ (Scope) থেকে ভেরিয়েবল অ্যাক্সেসের চেষ্টা"
            ]
            # NameError: name 'my_variable' is not defined. Did you mean: '...'
            match = re.search(r"name '(\w+)' is not defined", exc_msg)
            if match:
                var_name = match.group(1)
                # traceback ফ্রেম থেকে local ভেরিয়েবলসমূহ খোঁজা
                tb = exc.__traceback__
                local_names = []
                while tb:
                    local_names.extend(tb.tb_frame.f_locals.keys())
                    local_names.extend(tb.tb_frame.f_globals.keys())
                    tb = tb.tb_next
                
                similar = cls.find_similar_names(var_name, list(set(local_names)))
                if similar:
                    analysis["suggestion"] = f"বানান ভুল হয়েছে? আপনি কি <strong>{', '.join(similar)}</strong> বুঝাতে চেয়েছেন?"

        # AttributeError (অবজেক্টের মেথড/প্রোপার্টি টাইপো)
        elif exc_type == "AttributeError":
            analysis["category"] = "attribute_error"
            analysis["possible_causes"] = [
                "অবজেক্টে এই নামে কোনো মেথড বা প্রোপার্টি নেই",
                "মেথড বা প্রোপার্টির বানানে টাইপো",
                "অবজেক্টটি None (NoneType) হয়ে আছে"
            ]
            match = re.search(r"object has no attribute '(\w+)'", exc_msg)
            if match:
                attr_name = match.group(1)
                # Traceback থেকে অবজেক্টের টাইপ জানার চেষ্টা করা
                tb = exc.__traceback__
                last_tb = tb
                while last_tb and last_tb.tb_next:
                    last_tb = last_tb.tb_next
                
                if last_tb:
                    frame = last_tb.tb_frame
                    # কোড লাইন ইভালুয়েট করার চেষ্টা করে অবজেক্ট বের করা
                    for var_val in frame.f_locals.values():
                        if var_val is not None:
                            attrs = dir(var_val)
                            similar = cls.find_similar_names(attr_name, attrs)
                            if similar:
                                type_name = type(var_val).__name__
                                analysis["suggestion"] = f"বানান ভুল হয়েছে? <strong>{type_name}</strong> অবজেক্টের জন্য আপনি কি <strong>{', '.join(similar)}</strong> বুঝাতে চেয়েছেন?"
                                break

        # Database query error
        elif "QueryError" in exc_type or "ProgrammingError" in exc_type or "OperationalError" in exc_type:
            analysis["category"] = "database"
            analysis["possible_causes"] = [
                "SQL কুয়েরিতে সিনট্যাক্স এরর",
                "ডাটাবেসে টেবিল বা কলামের অস্তিত্ব নেই",
                "MySQL সংযোগ বিচ্ছিন্ন বা কনফিগ ভুল"
            ]
            analysis["suggestion"] = "আপনার database.sqlite ফাইল বা MySQL টেবিল স্কিমা চেক করুন। কলামের নাম বানানে ভুল হতে পারে।"

        # ModuleNotFoundError / ImportError
        elif exc_type in ("ModuleNotFoundError", "ImportError"):
            analysis["category"] = "import"
            analysis["possible_causes"] = [
                "লাইব্রেরিটি pip দিয়ে ইনস্টল করা হয়নি",
                "প্রজেক্ট ডিরেক্টরিতে ফাইলের নাম ভুল"
            ]
            match = re.search(r"No module named '(\w+)'", exc_msg)
            if match:
                mod_name = match.group(1)
                analysis["suggestion"] = f"টার্মিনালে <strong>pip install {mod_name}</strong> কমান্ডটি দিয়ে মডিউলটি ইনস্টল করুন।"

        return analysis

    @classmethod
    def render(cls, exc: Exception) -> str:
        """এররের বিস্তারিত এনালাইসিস করে একটি দৃষ্টিনন্দন এইচটিএমএল পেজ রিটার্ন করে"""
        exc_type = type(exc).__name__
        exc_msg = str(exc)

        # Traceback থেকে ফাইল ও লাইন নম্বর বের করা (সর্বশেষ ফ্রেম)
        tb = exc.__traceback__
        last_tb = tb
        while last_tb and last_tb.tb_next:
            last_tb = last_tb.tb_next

        filepath = "Unknown File"
        line_no = 0
        if last_tb:
            filepath = last_tb.tb_frame.f_code.co_filename
            line_no = last_tb.tb_lineno

        # কোড কনটেক্সট রিড করা
        code_context = cls.get_code_context(filepath, line_no) if line_no else ""

        # এরর এনালাইসিস করা
        analysis = cls.analyze_exception(exc)

        # সার্চ লিঙ্ক তৈরি
        search_query = urllib.parse.quote(f"Python {exc_type}: {exc_msg}")
        google_url = f"https://www.google.com/search?q={search_query}"
        so_url = f"https://stackoverflow.com/search?q={search_query}"

        # পরিবেশের স্ন্যাপশট (সুরক্ষিত উপায়ে মাস্কিং করা)
        env_snapshot = []
        for k, v in os.environ.items():
            if any(term in k.lower() for term in ("key", "pass", "secret", "token", "auth")):
                val_clean = "******** (Masked)"
            else:
                val_clean = str(v)
            env_snapshot.append((k, val_clean))

        # HTML View
        html_out = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>🚨 {exc_type} Detected - Intelligent Error View</title>
    <style>
        body {{
            background: #1e1e24;
            color: #dfe0e6;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #25252f;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            border-top: 5px solid #ff595e;
            overflow: hidden;
        }}
        .header {{
            background: #2d2d3a;
            padding: 24px;
            border-bottom: 1px solid #38384a;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{
            margin: 0;
            color: #ff595e;
            font-size: 22px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .btn-search {{
            display: inline-block;
            text-decoration: none;
            padding: 6px 14px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            color: #fff;
            transition: opacity 0.2s;
        }}
        .btn-search:hover {{ opacity: 0.9; }}
        .btn-google {{ background: #4285F4; margin-right: 8px; }}
        .btn-so {{ background: #F48024; }}
        .content {{ padding: 24px; }}
        .message-box {{
            background: #2d2d3a;
            border-left: 4px solid #ff595e;
            padding: 16px;
            border-radius: 4px;
            font-size: 15px;
            margin-bottom: 24px;
        }}
        .meta {{
            color: #aaa;
            font-size: 13px;
            margin-bottom: 24px;
            font-family: monospace;
        }}
        .code-container {{
            background: #141419;
            padding: 16px;
            border-radius: 6px;
            border: 1px solid #2d2d38;
            overflow-x: auto;
            margin-bottom: 24px;
        }}
        .code-container pre {{
            margin: 0;
            font-family: 'Consolas', 'Fira Code', monospace;
            font-size: 13px;
            color: #a9ff68;
        }}
        .suggestion-box {{
            background: rgba(82, 183, 136, 0.1);
            border-left: 4px solid #52b788;
            padding: 16px;
            border-radius: 4px;
            color: #95e1d3;
            margin-bottom: 24px;
        }}
        .suggestion-box strong {{ color: #52b788; font-size: 16px; display: block; margin-bottom: 6px; }}
        .traceback-title {{
            font-weight: bold;
            cursor: pointer;
            margin-bottom: 12px;
            display: inline-block;
            color: #9d4edd;
        }}
        .env-title {{
            font-weight: bold;
            cursor: pointer;
            margin-top: 24px;
            margin-bottom: 12px;
            display: inline-block;
            color: #4cc9f0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 8px;
        }}
        th, td {{
            padding: 6px 10px;
            border-bottom: 1px solid #2d2d38;
            text-align: left;
        }}
        th {{ color: #888; }}
        td.key {{ color: #ffb703; font-family: monospace; width: 30%; }}
        td.val {{ color: #ddd; font-family: monospace; word-break: break-all; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚨 {exc_type} Detected</h1>
            <div>
                <a href="{google_url}" target="_blank" class="btn-search btn-google">🔍 Google Search</a>
                <a href="{so_url}" target="_blank" class="btn-search btn-so">🥞 StackOverflow</a>
            </div>
        </div>
        
        <div class="content">
            <div class="message-box">
                <strong>Error Message:</strong> {exc_msg}
            </div>
            
            <div class="meta">
                <strong>File:</strong> {filepath}<br>
                <strong>Line:</strong> {line_no}
            </div>

            {f'''
            <div class="suggestion-box">
                <strong>💡 Intelligent Solution:</strong>
                {analysis['suggestion']}
            </div>
            ''' if analysis['suggestion'] else ''}

            {f'''
            <div class="code-container">
                <div style="color: #ffb703; font-weight: bold; font-size: 11px; margin-bottom: 8px; font-family: monospace;">💻 Code Context:</div>
                <pre>{code_context}</pre>
            </div>
            ''' if code_context else ''}

            <details>
                <summary class="traceback-title">🔍 View Detailed Traceback</summary>
                <pre style="background: #141419; padding: 12px; border-radius: 6px; border: 1px solid #2d2d38; color: #ff595e; font-family: monospace; font-size: 12px; overflow-x: auto;">{"".join(traceback.format_exception(type(exc), exc, exc.__traceback__))}</pre>
            </details>

            <details>
                <summary class="env-title">🌍 View Environment Snapshot</summary>
                <div style="background: #181822; padding: 12px; border-radius: 6px; border: 1px solid #2d2d38; max-height: 250px; overflow-y: auto;">
                    <table>
                        <thead>
                            <tr>
                                <th>Variable</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(f'<tr><td class="key">{k}</td><td class="val">{v}</td></tr>' for k, v in env_snapshot)}
                        </tbody>
                    </table>
                </div>
            </details>
        </div>
    </div>
</body>
</html>
"""
        return html_out
