<p align="center">
  <img src="public/static/images/logo.png" alt="PyFlow Logo" width="180" style="border-radius: 24px;" />
</p>

# PyFlow — Premium Custom Python MVC & FastAPI Framework 🚀
### Version 3.1.0 (Latest Release)

🌐 **Live Demo (লাইভ ডেমো):** [https://pyflow.nexterp.bd/](https://pyflow.nexterp.bd/) | 🛠️ **[Installation Guide (ইনস্টলেশন গাইড)](INSTALL.md)**


*   **📖 Read the [PyFlow Q&A FAQ (২৫টি প্রশ্নোত্তর)](FAQ.md) for quick architecture, database pool, dynamic html, and scaling answers.**
*   **📖 বাংলা এবং ইংরেজি বিস্তারিত প্রশ্নোত্তর দেখতে পড়ুন [PyFlow FAQ (২৫টি প্রশ্নোত্তর)](FAQ.md)।**


[বাংলা বিবরণ নিচে দেওয়া হয়েছে]

**PyFlow** is a lightweight, highly secure, and performance-optimized Python MVC framework built from scratch using Python's standard libraries, now featuring a seamless side-by-side **FastAPI** integration via a custom ASGI bridge.

PyFlow brings the elegance of modern PHP MVC frameworks (like Laravel) to Python, combined with the high-performance async API capabilities of FastAPI.

---

## 🌟 Key Features (মূল সুবিধাসমূহ)
- **Multi-Database Engine & Grammar Architecture (New in v3.1.0):** Run SQLite, MySQL, and PostgreSQL simultaneously in a single application (`Database.connection('mysql')`, `Database.connection('pgsql')`). Dialect-specific SQL & Schema Grammars compile ANSI, MySQL (backtick/JSON/date), PostgreSQL (double-quote/JSONB/@>/date), and SQLite queries automatically. Models bind dynamically to any connection via `Model.connection`.
- **Multi-Driver Database Pool:** Native thread-safe connection pooling for SQLite (with WAL mode), MySQL, and PostgreSQL.
- **Atomic Transactions Manager:** Database transactions block with context manager (`with Database.transaction()`), `@atomic` decorator, partial rollback using named `SAVEPOINT`, and mail/notify-safe hooks (`on_commit` / `on_rollback`).
- **Precision Financial Math:** Floating-point free exact calculations with `Money` class and automated Number-to-Words translation helpers in both Bangla and English.
- **Jinja/Blade-inspired Template Engine:** Supports layout inheritance (`@extends`, `@section`, `@yield`), `@include`, conditional loops, and auto-XSS escaping.
- **Custom ORM & Query Builder:** Fluent, SQL injection-proof database wrapper powered by dialect-aware Grammars.
- **FastAPI Integration:** Mounted on the same port (8000) under `/api/*` with Swagger docs at `/api/docs`.
- **Secure Security Shield:** Features built-in CSRF protection, rate limiting, PBKDF2-SHA256 password hashing, and session fixation defense.
- **Exhaustive Unit Tests:** Over 210+ rigorous unit tests cover router, validation, transactions, multi-database pool, grammars, and math classes.
- **Debug Bar:** Developer diagnostics bar displaying execution times, active database queries, and session logs.

### 2. Newly Integrated Advanced Features 🚀
- **FastAPI Side-by-Side Integration:** Mounted on the same port (8000) under `/api/*` using an ASGI-to-WSGI gateway. Swagger interactive API documentation is available at `/api/docs`.
- **Request Validator Engine:** Dedicated validator (`core/validator.py`) with support for rules like `required`, `email`, `numeric`, `min`, `max`, and `unique:table,column`.
- **Nested Transactions Manager:** SQL `SAVEPOINT` implementation in `core/database.py` allowing nested database transaction blocks safely.
- **System Settings Panel:** Dynamic key-value configuration manager (`app/models/setting_model.py`) with dynamic cache eviction.
- **Activity Logs / Audit Trail:** Automatic tracking of user logins, logouts, registry modifications, and security events, mapping the IP address and User-Agent.
- **API Key Management:** Laravel Sanctum-style API token generator. Tokens are hashed using SHA-256 in the database. Supports dual authentication (JWT Bearer Token and `X-API-Key` headers) for all FastAPI endpoints.
- **Advanced Logging Engine:** Adapts structured PHP logger logic to Python, logging request IPs, referers, active sessions, and errors to `storage/logs/` and displaying them in the Debug Bar.
- **Database Seeders & Factories:** Generates test database records programmatically using dynamic seeder classes and active factories. Integrated into the CLI.
- **Queue & Background Jobs:** Reliable database-backed queueing system running concurrent tasks through a standalone background worker. Integrated into the CLI.
- **Task Scheduler (Cron Job):** Executes registered cron-like callables at specific time intervals or specific daily times. Integrated into the CLI.
- **Native WebSocket Support:** ASGI bridge maps websocket connections directly to FastAPI for ultra-fast bi-directional communication (e.g. at `/ws`).

---

## 🗄️ Multi-Database Support & Grammar Architecture (v3.1.0) 🚀

PyFlow 3.1.0 introduces an enterprise-grade **Multi-Database Connection Manager & SQL Grammar Compiler Architecture**, allowing your application to seamlessly interact with multiple databases (SQLite, MySQL, and PostgreSQL) simultaneously within a single project.

### 1. Supported Database Engines
| Database Engine | Driver | Supported Features |
|:---|:---|:---|
| **SQLite 3** | `sqlite3` (built-in) | Thread-local pooling, Write-Ahead Logging (WAL mode), Foreign Keys enforcement, in-memory (`:memory:`) support. |
| **MySQL / MariaDB** | `MySQLdb` (`mysqlclient`) | Thread-safe connection pool, backtick escaping (`` `column` ``), native JSON queries (`JSON_CONTAINS`), DATE functions, `utf8mb4` full unicode. |
| **PostgreSQL** | `psycopg2` | Thread-safe connection pool, double quote escaping (`"column"`), JSONB containment (`@>`), fast primary key returning (`RETURNING "id"`), and cast filters (`::date`). |

### 2. Simultaneous Multi-Database Usage
You can query different databases within the same request or background job with zero friction:
```python
from core.database import Database

# 1. Query the default database (e.g. SQLite)
users = Database.table("users").where("status", "active").get()

# 2. Query MySQL ERP / Orders database
orders = Database.connection("mysql").table("orders").where("total", ">", 1000).get()

# 3. Insert audit logs into PostgreSQL analytics database
Database.connection("pgsql").table("audit_logs").insert({
    "action": "order.checkout",
    "user_id": 42,
    "ip_address": "127.0.0.1"
})
```

### 3. Model-Level Connection Binding
Every ORM Model can be bound to a specific database connection via the `connection` attribute:
```python
from core.model import Model

class User(Model):
    table_name = "users"
    # uses default connection

class Order(Model):
    table_name = "orders"
    connection = "mysql"  # automatically routes all queries to MySQL pool

class AuditLog(Model):
    table_name = "audit_logs"
    connection = "pgsql"  # automatically routes all queries to PostgreSQL pool

# Queries automatically route to their designated databases:
recent_orders = Order.where("status", "paid").limit(10).get()
recent_logs = AuditLog.where("severity", "critical").get()
```

### 4. Dialect-Specific SQL & Schema Grammars
Queries and DDL migrations are compiled dynamically based on the active connection's grammar compiler:
- **Identifier Wrapping:** MySQL wraps identifiers with backticks (`` `table`.`column` ``), while PostgreSQL and SQLite wrap with standard double quotes (`"table"."column"`).
- **Date Functions:** `where_date("created_at", "2026-10-24")` compiles to `DATE(col) = ?` in MySQL, `CAST(col AS DATE) = ?` in PostgreSQL, and `strftime('%Y-%m-%d', col) = ?` in SQLite.
- **JSON Queries:** `where_json("payload->status", "active")` compiles to `JSON_CONTAINS()` in MySQL and `@>` in PostgreSQL.
- **Primary Key Return:** PostgreSQL executes `RETURNING "id"` while MySQL and SQLite resolve the newly created primary key automatically.

### 5. Multi-Database Transactions & Named Savepoints
Atomic transactions can be opened on the default connection or any specific connection with automatic `SAVEPOINT` nesting:
```python
from core.database import Database, atomic

# Context manager on default connection
with Database.transaction():
    Database.table("accounts").where("id", 1).decrement("balance", 500)
    
    with Database.transaction():  # Named SAVEPOINT created automatically
        Database.table("transfers").insert({"amount": 500})

# Transaction on a specific connection (e.g. MySQL)
with Database.connection("mysql").transaction():
    Order.create({"user_id": 1, "amount": "150.00"})

# Function decorator
@atomic(connection="mysql")
def process_order(order_data):
    # entire function runs inside an isolated MySQL transaction
    ...
```

### 6. Environment Configuration (`.env`)
```ini
# Default active connection (sqlite, mysql, or pgsql)
DB_CONNECTION=sqlite

# SQLite Connection
DB_NAME=storage/database.sqlite

# MySQL Connection Settings
DB_MYSQL_HOST=127.0.0.1
DB_MYSQL_PORT=3306
DB_MYSQL_DATABASE=pyflow_db
DB_MYSQL_USERNAME=root
DB_MYSQL_PASSWORD=secret
DB_MYSQL_POOL_SIZE=10

# PostgreSQL Connection Settings
DB_PGSQL_HOST=127.0.0.1
DB_PGSQL_PORT=5432
DB_PGSQL_DATABASE=pyflow_pg
DB_PGSQL_USERNAME=postgres
DB_PGSQL_PASSWORD=secret
DB_PGSQL_POOL_SIZE=10
```

---

## 📂 Folder Structure (ফোল্ডার আর্কিটেকচার)
```
pyflow/
├── app/
│   ├── api/             # FastAPI sub-application routes & schemas
│   ├── controllers/     # AuthController, UserController, SettingController...
│   ├── models/          # User, Setting, ActivityLog, ApiKey Models (Multi-DB bound)
│   └── views/           # .html View templates (admin, settings, api_keys, logs)
├── benchmarks/          # Performance benchmark suite (router, grammars, multi-DB)
├── config/
│   ├── config.py        # Global environment configuration loader
│   ├── database.py      # Multi-database driver and pool configurations
│   └── routes.py        # Main PyFlow web routes configuration
├── core/                # Core engines (router, ORM, validator, bridge)
│   └── database/        # Multi-database manager, drivers, and dialect grammars
│       ├── contracts/   # ConnectionInterface, GrammarInterface, SchemaGrammarInterface
│       ├── drivers/     # SqliteConnection, MySqlConnection, PostgresConnection
│       ├── grammar/     # BaseGrammar, MySqlGrammar, PostgresGrammar, SqliteGrammar
│       ├── schema/      # BaseSchemaGrammar, MySQL, PostgreSQL, SQLite DDL Compilers
│       └── manager.py   # DatabaseManager (runtime dynamic multi-DB switcher)
├── public/
│   ├── index.py         # WSGI production entry point
│   └── static/          # CSS/JS/images assets
├── storage/             # Log files, session database, sqlite database storage
├── tests/               # 210+ comprehensive unit and multi-DB tests
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
cp .env.example .env
```

### 4. Run Database Migrations
Initialize database tables and run migration files:
```bash
python migrate.py
```

### 5. Run the Server
Launch the development ASGI server (Uvicorn-based):
```bash
python run.py
```
Open your browser and navigate to:
- **Web Dashboard:** `http://127.0.0.1:8000/dashboard`
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

### ১. এন্টারপ্রাইজ মাল্টি-ডাটাবেজ ইঞ্জিন ও গ্রামার আর্কিটেকচার (Multi-Database & Grammars v3.1.0) 🚀
PyFlow 3.1.0-এ NovaFlow-এর অনুরূপ কিন্তু পাইথনের শক্তিতে আরও উন্নত **Multi-Database Connection Manager & SQL Grammar Compiler Architecture** যুক্ত করা হয়েছে।
- **একসাথে ৩টি ডাটাবেজ সমান্তরালভাবে ব্যবহার:** একটি অ্যাপ্লিকেশনে একই সাথে SQLite (লোকাল/ক্যাশ), MySQL (মেইন ট্রানজেকশন/অর্ডার), এবং PostgreSQL (অডিট লগ/অ্যানালিটিক্স) চালানো যায়।
- **ডায়ালেক্ট অনুযায়ী SQL কম্পাইলার:** MySQL ব্যাকটিক (`` ` ``), Postgres ডাবল কোট (`" "`), ডেট ফিল্টার (`DATE()` বনাম `CAST AS DATE` বনাম `strftime`), এবং JSON কুয়েরি কম্পাইলার।
- **মডেল লেভেলে ডাটাবেজ বাউন্ডিং:** `Model.connection = "mysql"` লিখে যেকোনো মডেলকে নির্দিষ্ট ডাটাবেজের সাথে যুক্ত করা যায়।
- **থ্রেড-সেফ কানেকশন পুলিং:** হাই-কনকারেন্ট রিকোয়েস্টে ডাটাবেস হ্যান্ডশেক ওভারহেড দূর করতে থ্রেড-সেফ পুলিং ও SQLite WAL মোড।

### ২. ফাস্ট-এপিআই (FastAPI) ইন্টিগ্রেশন
একটি রেডিমেড WSGI-to-ASGI ব্রিজের মাধ্যমে PyFlow and FastAPI একই পোর্টে (৮০০০) পাশাপাশি রান করে। সব API রিকোয়েস্ট `/api/*` পাথে FastAPI হ্যান্ডেল করে এবং ইন্টারেক্টিভ Swagger ডক্স পাওয়া যায় `/api/docs`-এ।

### ৩. ফর্ম ভ্যালিডেটর ইঞ্জিন (Request Validator)
ইনপুট স্যানিটাইজেশন ও ডেটা ভ্যালিডেশনের জন্য `Validator` ক্লাস রয়েছে। এটি `required`, `email`, `numeric`, `min`, `max`, এবং ডাটাবেস চেক করার জন্য `unique:table,column` রুলস সাপোর্ট করে।

### ৪. নেস্টেড ডাটাবেস ট্রানজেকশন (Nested Transactions)
ডাটাবেস লেভেলে জটিল কোয়েরি অপারেশনের জন্য nested transaction বা SQL `SAVEPOINT` ইমপ্লিমেন্ট করা হয়েছে। এর ফলে আংশিক কুয়েরি এরর হলে সম্পূর্ণ ট্রানজেকশন রোলব্যাক না করে নির্দিষ্ট সেভপয়েন্টে ফেরত যাওয়া যায়।

### ৫. এপিআই কী ও অডিট লগ (API Key Management)
ব্যবহারকারীরা সরাসরি ড্যাশবোর্ড থেকে এপিআই কী (`pm_sk_...`) তৈরি এবং বাতিল করতে পারেন। এটি ডাটাবেসে SHA-256 হ্যাশ করা থাকে। এই কী দিয়ে FastAPI এন্ডপয়েন্টগুলোতে `X-API-Key` হেডারের মাধ্যমে অথেন্টিকেট করা যায়।

### ৬. অ্যাক্টিভিটি লগ (Audit Trail)
ইউজার সিকিউরিটি নিশ্চিত করতে অ্যাপ্লিকেশনের সমস্ত কার্যকলাপ (লগইন, লগআউট, সেটিংস পরিবর্তন ইত্যাদি) স্বয়ংক্রিয়ভাবে ইউজারের আইপি এবং ইউজার এজেন্টসহ ডাটাবেসে ট্র্যাকিং লগ তৈরি করে।

### ৭. উন্নত লগিং সিস্টেম (Advanced Logging)
NovaFlow-এর `Logger.php`-র অনুরূপ পাইথন সংস্করণ। এটি আইপি, সেশন আইডি এবং ইউজার এজেন্ট সহ সব স্ট্যান্ডার্ড লেভেলে লগ তৈরি করে যা ব্রাউজারের ফুটবার ডিবাগ বারেও দেখা যায়।

### ৮. ডাটাবেস সিডার ও ফ্যাক্টরি (Database Seeders & Factories)
সহজে ডামি ডেটা তৈরি ও ডাটাবেস টেস্ট করার জন্য ডাইনামিক সিডার ও ফ্যাক্টরি মেকানিজম। CLI অপশন ৯ এর মাধ্যমে এক্সিকিউট করা যায়।

### ৯. ব্যাকগ্রাউন্ড কিউ এবং জব (Queue & Background Jobs)
মেল পাঠানো বা ভারী প্রসেস ব্যাকগ্রাউন্ডে চালানোর জন্য ডাটাবেস-ব্যাকড কিউ এবং থ্রেডেড ওয়ার্কার। CLI অপশন ১০ এর মাধ্যমে রান করা যায়।

### ১০. টাস্ক সিডিউলার (Task Scheduler)
প্রতি মিনিটে বা নির্দিষ্ট সময়ে ব্যাকগ্রাউন্ড টাস্ক রান করানোর জন্য শিডিউলার ইঞ্জিন। CLI অপশন ১১ এর মাধ্যমে চালানো যায়।

### ১১. রিয়েল-টাইম ওয়েবসকেট (WebSockets)
ASGI ব্রিজের সাহায্যে বাই-ডিরেকショナル রিয়েল-টাইম ওয়েবসকেট গেটওয়ে (যেমন `/ws` এন্ডপয়েন্টে)।

### ১২. ইন্টারঅ্যাক্টিভ সিএলআই অ্যাসিস্ট্যান্ট (cli.py) 🖥️
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

## 🖥️ PyFlow CLI - বিস্তারিত নির্দেশিকা (Detailed CLI Guide)

PyFlow-তে ডেভলপমেন্টের কাজ সহজ করার জন্য Laravel Artisan-এর মতো একটি ইন্টারঅ্যাক্টিভ ও ডাইনামিক কমান্ড লাইন ইন্টারফেস (CLI) অ্যাসিস্ট্যান্ট রয়েছে।

### কিভাবে রান করবেন?
টার্মিনালে প্রজেক্টের রুট ডিরেক্টরিতে গিয়ে নিচের কমান্ডটি রান করুন:
```bash
python cli.py
```
এটি রান করার পর একটি সুন্দর মেনু দেখতে পাবেন, যেখান থেকে নম্বর সিলেক্ট করে আপনি বিভিন্ন কাজ সম্পন্ন করতে পারবেন।

### ফিচারসমূহের বিস্তারিত বিবরণ:

#### ১. View Registered Routes (রেজিস্টার্ড রাউট তালিকা)
- **কাজ:** আপনার অ্যাপ্লিকেশনে কোন কোন ইউআরএল (URL) রেজিস্টার করা আছে তা দেখতে এটি ব্যবহার করা হয়।
- **আউটপুট:** এটি `config/routes.py` থেকে সমস্ত রাউট লোড করে এবং টার্মিনালে নিম্নোক্ত কলামসহ একটি সুন্দর টেবিল দেখায়:
  - **Method:** GET, POST, PUT, DELETE ইত্যাদি।
  - **Path:** ইউজার যে ইউআরএল ব্রাউজ করবেন (যেমন `/dashboard`, `/settings`)।
  - **Handler:** রাউটটি কোন কন্ট্রোলার ও মেথড দ্বারা হ্যান্ডেল হচ্ছে।
  - **Name:** রাউটের ইউনিক নাম।
  - **Middleware:** এই রাউটে কোনো মিডলওয়্যার (যেমন `auth`, `guest`) সক্রিয় আছে কিনা।

#### ২. View Database Tables (ডাটাবেস টেবিল তালিকা)
- **কাজ:** আপনার কনফিগার করা ডাটাবেসের (SQLite বা MySQL) সকল টেবিল দেখতে এটি সাহায্য করে।
- **আউটপুট:** ডাটাবেসে তৈরি হওয়া টেবিলগুলোর নাম ক্রমানুসারে লিস্ট আকারে প্রিন্ট করে।

#### ৩. Database Summary Report (ডাটাবেস রেকর্ড সামারি)
- **কাজ:** ডাটাবেসে ডেটা লোড বা রেকর্ডের অবস্থা দেখতে এটি কার্যকর।
- **আউটপুট:** প্রতিটি টেবিলে বর্তমানে মোট কতটি রো (Row) বা রেকর্ড সংরক্ষিত আছে তা গণনা করে লাইভ সামারি রিপোর্ট প্রদর্শন করে।

#### ৪. Generate Model File (ওআরএম মডেল জেনারেটর)
- **কাজ:** নতুন ওআরএম (ORM) মডেল দ্রুত স্কাফোল্ড বা জেনারেট করে।
- **ধাপসমূহ:**
  1. অপশনটি সিলেক্ট করার পর মডেলের নাম চাইবে (যেমন: `Product`)।
  2. এরপর টেবিলের নাম জানতে চাইবে (যেমন: `products`)। (কিছু না লিখে এন্টার দিলে স্বয়ংক্রিয়ভাবে মডেলের নামের শেষে 's' যুক্ত করে টেবিল নাম ধরে নেয়)।
- **আউটপুট:** এটি `app/models/product_model.py` ফাইলটি তৈরি করবে, যা `core.model.Model` ক্লাসকে এক্সটেন্ড করে এবং ওআরএম কোয়েরির জন্য প্রস্তুত থাকে।

#### ৫. Generate Controller File (কন্ট্রোলার জেনারেটর)
- **কাজ:** নতুন কন্ট্রোলার টেমপ্লেট দ্রুত তৈরি করে।
- **ধাপসমূহ:**
  1. কন্ট্রোলারের নাম চাইবে (যেমন: `Product`)।
- **আউটপুট:** এটি `app/controllers/product_controller.py` ফাইল তৈরি করবে। ফাইলটিতে স্বয়ংক্রিয়ভাবে `ProductController` ক্লাস ডিক্লেয়ার করা থাকবে এবং ডিফল্ট ভিউ লোড করার জন্য একটি `index` অ্যাকশন বা মেথড তৈরি হবে।

#### ৬. System Health Check (সিস্টেম হেলথ চেক)
- **কাজ:** অ্যাপ্লিকেশনের রানটাইম এনভায়রনমেন্ট এবং কনফিগারেশন সঠিক আছে কিনা তা এক ক্লিকে ডায়াগনস্টিক চেক করে।
- **যাচাইকৃত বিষয়সমূহ:**
  - পাইথন রানটাইম ভার্সন (>= 3.9) ঠিক আছে কিনা।
  - `storage/logs` এবং `storage/sessions` ফোল্ডারের রাইট পারমিশন (Writable) সচল কিনা।
  - `.env` ফাইলটি ঠিকমতো তৈরি করা আছে কিনা।
  - ডাটাবেসের সাথে কানেকশন সফলভাবে হচ্ছে কিনা।
  - প্রত্যেকটির শেষে সবুজ রঙের `[PASS]` অথবা লাল রঙের `[FAIL]` স্ট্যাটাস দেখায়।

#### ৭. Clear Logs & Temp Sessions (লগ ও সেশন ক্যাশ ক্লিয়ার)
- **কাজ:** অ্যাপ্লিকেশনের জমা হওয়া অতিরিক্ত লগ ফাইল ও ক্যাশড ইউজার সেশন ক্লিয়ার করে ফ্রেশ স্টার্ট করতে সাহায্য করে।
- **আউটপুট:** এটি `storage/logs/` এবং `storage/sessions/` ডিরেক্টরির সমস্ত ফাইল ডিলিট করে। ডিলিট করার আগে এটি ব্যবহারকারীর কাছ থেকে `y/N` ইনপুট নিয়ে নিশ্চিত হয়ে নেয়।

#### ৮. Run Database Migrations (ডাটাবেস মাইগ্রেশন রান)
- **কাজ:** নতুন টেবিল তৈরি বা ডাটাবেস স্কিমা আপডেট করতে মাইগ্রেশন ফাইলগুলো রান করে।
- **আউটপুট:** এটি ব্যাকগ্রাউন্ডে `migrate.py` স্ক্রিপ্টকে এক্সিকিউট করে মাইগ্রেশনের ফলাফল স্ক্রিনে দেখায়।

#### ৯. Run Database Seeders (ডাটাবেস সিডার রান)
- **কাজ:** ডাটাবেসকে ডামি ডেটা দিয়ে পূর্ণ করার জন্য সিডার রান করে।
- **আউটপুট:** এটি `core/seeder.py` ব্যবহার করে `app/database/seeds/` ফোল্ডারের সিডারগুলো এক্সিকিউট করে এবং ফলাফল টার্মিনালে দেখায়।

#### ১০. Run Queue Worker (কিউ ওয়ার্কার রান)
- **কাজ:** ব্যাকগ্রাউন্ডে থাকা কাজগুলো প্রসেস করার জন্য কিউ ওয়ার্কার চালু করে।
- **আউটপুট:** এটি `queue_worker.py` স্ক্রিপ্টটি চালু করে এবং টার্মিনালে প্রসেসিং লগের লাইভ আপডেট দেখায় (বন্ধ করতে `Ctrl+C` প্রেস করতে হবে)।

#### ১১. Run Task Scheduler (টাস্ক সিডিউলার রান)
- **কাজ:** সময়ভিত্তিক রিকারিং টাস্ক বা ক্রন জবগুলো চালু করার জন্য সিডিউলার চালু করে।
- **আউটপুট:** এটি `scheduler_runner.py` স্ক্রিপ্ট রান করে প্রতি সেকেন্ডে ব্যাকগ্রাউন্ডে শিডিউল চেক করতে থাকে।

---

## 💻 CLI এবং কোড ব্যবহারের উদাহরণ

### রাউট রেজিস্টার করা (`config/routes.py`):
```python
router.get("/settings", action(SettingController, "index"), name="settings")
router.post("/settings", action(SettingController, "update"), name="settings.update")
```

### ডাটাবেস ও মাল্টি-ডিবি ব্যবহারের উদাহরণ:

#### ক) একই সাথে একাধিক ডাটাবেজে কুয়েরি চালানো:
```python
from core.database import Database

# ১. ডিফল্ট ডাটাবেজে কুয়েরি (যেমন SQLite)
users = Database.table("users").where("status", "active").get()

# ২. সরাসরি MySQL ডাটাবেজে কুয়েরি (কানেকশন সুইচিং)
orders = Database.connection("mysql").table("orders").where("total", ">", 1000).get()

# ৩. সরাসরি PostgreSQL ডাটাবেজে ইনসার্ট
Database.connection("pgsql").table("audit_logs").insert({
    "action": "order.checkout",
    "user_id": 42,
    "ip_address": "192.168.1.1"
})
```

#### খ) মডেল লেভেলে ডাটাবেজ বাইন্ডিং (ORM Model):
```python
from core.model import Model

class User(Model):
    table_name = "users"
    # ডিফল্ট কানেকশন

class Order(Model):
    table_name = "orders"
    connection = "mysql"  # স্বয়ংক্রিয়ভাবে MySQL কানেকশনে যাবে

class AuditLog(Model):
    table_name = "audit_logs"
    connection = "pgsql"  # স্বয়ংক্রিয়ভাবে PostgreSQL কানেকশনে যাবে

# মডেল কুয়েরি চালালে স্বয়ংক্রিয়ভাবে সংশ্লিষ্ট ডাটাবেজে এক্সিকিউট হবে:
recent_orders = Order.where("status", "paid").limit(10).get()
recent_logs = AuditLog.where("severity", "critical").get()
```

#### গ) ডাটাবেস ট্রানজেকশন ও নেস্টেড সেভপয়েন্ট:
```python
from core.database import Database, atomic

# ১. কনটেক্সট ম্যানেজার দিয়ে নেস্টেড ট্রানজেকশন
with Database.transaction():
    Database.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("John", "john@example.com"))
    
    with Database.transaction():  # আংশিক রোলব্যাকের জন্য স্বয়ংক্রিয় SAVEPOINT
        Database.execute("UPDATE settings SET value = ? WHERE key = ?", ("dark", "theme"))

# ২. স্পেসিফিক কানেকশনে ট্রানজেকশন (যেমন MySQL)
with Database.connection("mysql").transaction():
    Order.create({"user_id": 1, "amount": "150.00"})

# ৩. ফাংশন ডেকোরেটর
@atomic(connection="mysql")
def process_order(order_data):
    # সম্পূর্ণ ফাংশনটি একটি সেফ MySQL ট্রানজেকশনের ভেতর চলবে
    ...
```

### এপিআই কী অথেন্টিকেশন হেডার টেস্ট:
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/api/users' \
  -H 'accept: application/json' \
  -H 'X-API-Key: pm_sk_your_plaintext_token_here'
```

---

## 🌐 Production Deployment Guide (প্রোডাকশন ডেপ্লয়মেন্ট গাইড)

ডেভেলপমেন্ট মোডে PyFlow সরাসরি পাইথন সার্ভারের সাহায্যে স্ট্যাটিক ফাইল ও অ্যাপ্লিকেশন রেসপন্স সার্ভ করে। কিন্তু প্রোডাকশন এনভায়রনমেন্টে উচ্চ কর্মক্ষমতা (Performance) এবং নিরাপত্তা নিশ্চিত করার জন্য নিম্নোক্ত নির্দেশিকা অনুসরণ করুন:

### ১. Nginx / Caddy দিয়ে স্ট্যাটিক ফাইল সরাসরি সার্ভ করা:
প্রোডাকশনে পাইথন কোডের মাধ্যমে স্ট্যাটিক ফাইল (`/static/*`) সার্ভ করা ধীরগতির এবং অতিরিক্ত মেমোরি খরচ করতে পারে। তাই Nginx বা Caddy ব্যবহার করে স্ট্যাটিক ফাইলগুলো সরাসরি ক্লায়েন্টকে সার্ভ করুন এবং অন্য সব রিকোয়েস্ট Uvicorn ASGI গেটওয়েতে রিডাইরেক্ট করুন।

**Nginx Configuration Example:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # স্ট্যাটিক ফাইলের পাথ (সরাসরি Nginx সার্ভ করবে)
    location /static/ {
        alias /path/to/pyflow/public/static/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    # বাকি সব রিকোয়েস্ট ASGI/WSGI গেটওয়েতে পাঠানো
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### ২. সেশন ফাইল লক সক্রিয়করণ:
PyFlow ফাইল-বেসড সেশন লকিং মেকানিজম ব্যবহার করে যা একাধিক সমান্তরাল AJAX রিকোয়েস্টের সময় রেস কন্ডিশন (Race Condition) প্রতিরোধ করে। প্রোডাকশন ট্রাফিকের জন্য এটি অত্যন্ত উপযোগী।

---

## 🤝 অবদান রাখুন
যেকোনো বাগ ফিক্স, ফিচার আইডিয়া বা ইমপ্রুভমেন্টের জন্য পুল রিকোয়েস্ট (Pull Request) পাঠাতে পারেন। 

## 📄 লাইসেন্স
এই প্রকল্পটি [MIT License](LICENSE) এর অধীনে ওপেন-সোর্স করা হয়েছে।
