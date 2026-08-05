# PyFlow — Premium Custom Python MVC & FastAPI Framework 🚀

[বাংলা বিবরণ নিচে দেওয়া হয়েছে]

**PyFlow** is a lightweight, highly secure, and performance-optimized Python MVC framework built from scratch using Python's standard libraries, now featuring a seamless side-by-side **FastAPI** integration via a custom ASGI bridge. 

PyFlow brings the elegance of modern PHP MVC frameworks (like Laravel) to Python, combined with the high-performance async API capabilities of FastAPI.

---

## 🌟 Key Features (মূল সুবিধাসমূহ)

### 1. Core PyFlow Features
- **Custom Template Engine:** Jinja/Blade-inspired template system supporting layout inheritance (`@extends`, `@section`, `@yield`), `@include`, conditional loops, and auto-XSS escaping.
- **Chained Query Builder & ORM:** SQL injection-proof active-record ORM supporting SQLite and MySQL with fluent syntax.
- **Robust Security Shield:** Features built-in CSRF protection, rate limiting (brute-force defense), PBKDF2-SHA256 password hashing, and session fixation defense.
- **Debug Bar:** Developer diagnostics bar displaying execution times, active database queries, and session logs.

### 2. Newly Integrated Advanced Features 🚀
- **FastAPI Side-by-Side Integration:** Mounted on the same port (8000) under `/api/*` using an ASGI-to-WSGI gateway. Swagger interactive API documentation is available at `/api/docs`.
- **Request Validator Engine:** Dedicated validator (`core/validator.py`) with support for rules like `required`, `email`, `numeric`, `min`, `max`, and `unique:table,column`.
- **Nested Transactions Manager:** SQL `SAVEPOINT` implementation in `core/database.py` allowing nested database transaction blocks safely.
- **System Settings Panel:** Dynamic key-value configuration manager (`app/models/setting_model.py`) with dynamic cache eviction.
- **Activity Logs / Audit Trail:** Automatic tracking of user logins, logouts, registry modifications, and security events, mapping the IP address and User-Agent.
- **API Key Management:** Laravel Sanctum-style API token generator. Tokens are hashed using SHA-256 in the database. Supports dual authentication (JWT Bearer Token and `X-API-Key` headers) for all FastAPI endpoints.

---

## 📂 Folder Structure (ফোল্ডার আর্কিটেকচার)
```
pyflow/
├── app/
│   ├── api/             # FastAPI sub-application routes & schemas
│   ├── controllers/     # AuthController, UserController, SettingController...
│   ├── models/          # User, Setting, ActivityLog, ApiKey Models
│   └── views/           # .html View templates (admin, settings, api_keys, logs)
├── config/
│   ├── config.py        # .env configuration loader
│   └── routes.py        # Main PyFlow web routes configuration
├── core/                # Core engines (router, ORM, validator, database, bridge)
├── public/
│   ├── index.py         # WSGI production entry point
│   └── static/          # CSS/JS/images assets
├── storage/             # Log files, session database, sqlite database storage
├── migrate.py           # Database migration runner
├── run.py               # Development ASGI server launcher (Uvicorn-based)
└── requirements.txt     # Python dependencies
```

---

## 🛠️ Installation & Setup (ইনস্টলেশন ও সেটআপ)

### 1. Clone the Project
```bash
git clone https://github.com/your-username/pyflow.git
cd pyflow
```

### 2. Install Dependencies
Make sure you have Python >= 3.10. Install libraries:
```bash
pip install -r requirements.txt
```

### 3. Setup Configuration
Copy the `.env.example` to `.env` and set up database credentials (SQLite is active by default):
```bash
cp .env.- **Web Dashboard:** `http://127.0.0.1:8000/dashboard`
- **FastAPI Swagger Docs:** `http://127.0.0.1:8000/api/docs`

### 6. Run the Interactive CLI Assistant 🖥️
PyFlow includes a colorful, menu-driven CLI assistant to manage routes, generate database models/controllers, check systems health, and run migrations:
```bash
python cli.py
```
This CLI supports:
- **View Registered Routes:** Prints all web URLs, request methods, controllers, and middlewares in a clean table.
- **View Database Tables:** Lists all active tables in SQLite or MySQL.
- **Database Summary Report:** Counts records across database tables dynamically.
- **Generate Model & Controller Files:** Quickly scaffold active record models (`app/models/*_model.py`) and controllers (`app/controllers/*_controller.py`).
- **System Health Check:** Verifies Python environment, write permissions, `.env` file, and active DB connections.
- **Clear Logs & Sessions:** Wipes `storage/logs/` and `storage/sessions/` clean.
- **Run Database Migrations:** Reuses migration engine to initialize and seed schemas.

---

---

# PyFlow — প্রিমিয়াম কাস্টম পাইথন এমভিসি ও ফাস্ট-এপিআই ফ্রেমওয়ার্ক 🇧🇩

**PyFlow** হলো কোনো অতিরিক্ত ভারী লাইব্রেরি ছাড়া, পাইথনের নিজস্ব স্ট্যান্ডার্ড মডিউলের ওপর ভিত্তি করে তৈরি একটি অত্যন্ত গতিশীল ও নিরাপদ MVC ফ্রেমওয়ার্ক। এতে কাস্টম এএসজিআই ব্রিজের (ASGI Bridge) মাধ্যমে একই পোর্টে **FastAPI** যুক্ত করা হয়েছে।

## 🌟 কাস্টম এবং অ্যাডভান্সড ফিচারসমূহ

### ১. ফাস্ট-এপিআই (FastAPI) ইন্টিগ্রেশন
একটি রেডিমেড WSGI-to-ASGI ব্রিজের মাধ্যমে PyFlow and FastAPI একই পোর্টে (৮০০০) পাশাপাশি রান করে। সব API রিকোয়েস্ট `/api/*` পাথে FastAPI হ্যান্ডেল করে এবং ইন্টারেক্টিভ Swagger ডক্স পাওয়া যায় `/api/docs`-এ।

### ২. ফর্ম ভ্যালিডেটর ইঞ্জিন (Request Validator)
ইনপুট স্যানিটাইজেশন ও ডেটা ভ্যালিডেশনের জন্য `Validator` ক্লাস রয়েছে। এটি `required`, `email`, `numeric`, `min`, `max`, এবং ডাটাবেস চেক করার জন্য `unique:table,column` রুলস সাপোর্ট করে।

### ৩. নেস্টেড ডাটাবেস ট্রানজেকশন (Nested Transactions)
ডাটাবেস লেভেলে জটিল কোয়েরি অপারেশনের জন্য nested transaction বা SQL `SAVEPOINT` ইমপ্লিমেন্ট করা হয়েছে। এর ফলে আংশিক কুয়েরি এরর হলে সম্পূর্ণ ট্রানজেকশন রোলব্যাক না করে নির্দিষ্ট সেভপয়েন্টে ফেরত যাওয়া যায়।

### ৪. এপিআই কী ও অডিট লগ (API Key Management)
ব্যবহারকারীরা সরাসরি ড্যাশবোর্ড থেকে এপিআই কী (`pm_sk_...`) তৈরি এবং বাতিল করতে পারেন। এটি ডাটাবেসে SHA-256 হ্যাশ করা থাকে। এই কী দিয়ে FastAPI এন্ডপয়েন্টগুলোতে `X-API-Key` হেডারের মাধ্যমে অথেন্টিকেট করা যায়।

### ৫. অ্যাক্টিভিটি লগ (Audit Trail)
ইউজার সিকিউরিটি নিশ্চিত করতে অ্যাপ্লিকেশনের সমস্ত কার্যকলাপ (লগইন, লগআউট, সেটিংস পরিবর্তন ইত্যাদি) স্বয়ংক্রিয়ভাবে ইউজারের আইপি এবং ইউজার এজেন্টসহ ডাটাবেসে ট্র্যাকিং লগ তৈরি করে।

### ৬. ইন্টারঅ্যাক্টিভ সিএলআই অ্যাসিস্ট্যান্ট (cli.py) 🖥️
Laravel Artisan-এর মতো PyFlow-তে রয়েছে একটি সম্পূর্ণ ফিচারযুক্ত টার্মিনাল মেনু অ্যাসিস্ট্যান্ট। রান করার নিয়ম:
```bash
python cli.py
```
এর মূল সুবিধাসমূহ:
- **রাউট লিস্ট (Route List):** অ্যাপ্লিকেশনের সমস্ত রেজিস্টার্ড রাউট ও মিডলওয়্যার একটি সুন্দর চার্টে প্রদর্শন করে।
- **মডেল ও কন্ট্রোলার জেনারেটর:** সহজে ওআরএম মডেল এবং নতুন কন্ট্রোলার টেমপ্লেট ফাইল তৈরি করে।
- **ডাটাবেস রিপোর্ট:** সব টেবিলের রো (Row) বা রেকর্ডের সংখ্যা লাইভ দেখায়।
- **সিস্টেম হেলথ চেক:** প্রজেক্ট ডিরেক্টরি পারমিশন, পাইথন কনফিগারেশন এবং ডাটাবেস সংযোগ এক ক্লিকে ভেরিফাই করে।
- **লগ ও সেশন ক্লিয়ার:** দ্রুত স্টোরেজ ফোল্ডার ক্যাশ ও সেশন ফাইলগুলো রিসেট করে।

---� Swagger ডক্স পাওয়া যায় `/api/docs`-এ।

### ২. ফর্ম ভ্যালিডেটর ইঞ্জিন (Request Validator)
ইনপুট স্যানিটাইজেশন ও ডেটা ভ্যালিডেশনের জন্য `Validator` ক্লাস রয়েছে। এটি `required`, `email`, `numeric`, `min`, `max`, এবং ডাটাবেস চেক করার জন্য `unique:table,column` রুলস সাপোর্ট করে।

### ৩. নেস্টেড ডাটাবেস ট্রানজেকশন (Nested Transactions)
ডাটাবেস লেভেলে জটিল কোয়েরি অপারেশনের জন্য nested transaction বা SQL `SAVEPOINT` ইমপ্লিমেন্ট করা হয়েছে। এর ফলে আংশিক কুয়েরি এরর হলে সম্পূর্ণ ট্রানজেকশন রোলব্যাক না করে নির্দিষ্ট সেভপয়েন্টে ফেরত যাওয়া যায়।

### ৪. এপিআই কী ও অডিট লগ (API Key Management)
ব্যবহারকারীরা সরাসরি ড্যাশবোর্ড থেকে এপিআই কী (`pm_sk_...`) তৈরি এবং বাতিল করতে পারেন। এটি ডাটাবেসে SHA-256 হ্যাশ করা থাকে। এই কী দিয়ে FastAPI এন্ডপয়েন্টগুলোতে `X-API-Key` হেডারের মাধ্যমে অথেন্টিকেট করা যায়।

### ৫. অ্যাক্টিভিটি লগ (Audit Trail)
ইউজার সিকিউরিটি নিশ্চিত করতে অ্যাপ্লিকেশনের সমস্ত কার্যকলাপ (লগইন, লগআউট, সেটিংস পরিবর্তন ইত্যাদি) স্বয়ংক্রিয়ভাবে ইউজারের আইপি এবং ইউজার এজেন্টসহ ডাটাবেসে ট্র্যাকিং লগ তৈরি করে।

---

## 💻 CLI এবং কোড ব্যবহারের উদাহরণ

### রাউট রেজিস্টার করা (`config/routes.py`):
```python
router.get("/settings", action(SettingController, "index"), name="settings")
router.post("/settings", action(SettingController, "update"), name="settings.update")
```

### ডাটাবেস ট্রানজেকশন কন্ট্রোল:
```python
from core.database import Database

with Database.transaction():
    # প্রথম কুয়েরি
    Database.execute("INSERT INTO users ...")
    
    with Database.transaction(): # নেস্টেড সেভপয়েন্ট ট্রানজেকশন
        Database.execute("UPDATE settings ...")
```

### এপিআই কী অথেন্টিকেশন হেডার টেস্ট:
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/users' \
  -H 'accept: application/json' \
  -H 'X-API-Key: pm_sk_your_plaintext_token_here'
```

---

## 🤝 অবদান রাখুন
যেকোনো বাগ ফিক্স, ফিচার আইডিয়া বা ইমপ্রুভমেন্টের জন্য পুল রিকোয়েস্ট (Pull Request) পাঠাতে পারেন। 

## 📄 লাইসেন্স
এই প্রকল্পটি [MIT License](LICENSE) এর অধীনে ওপেন-সোর্স করা হয়েছে।
