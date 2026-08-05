# PyFlow Framework - Frequently Asked Questions (FAQ) 📖

[বাংলা বিবরণ নিচে দেওয়া হয়েছে]

Welcome to the PyFlow FAQ page! This document covers common technical, architectural, performance, and scaling questions regarding PyFlow.

---

## English Version

### Q1: Will using plain HTML cause issues with dynamic pages?
**Answer:** No. PyFlow's template engine compiles loops and conditionals on the server. For frontend interactivity, you can use Vanilla JS, Alpine.js, or HTMX to build fully dynamic pages without the bloat of heavy JS frameworks.

### Q2: Can MySQL handle 2 Million+ records efficiently?
**Answer:** Yes. 2 Million rows is a very small volume for modern MySQL database engines. By applying proper indexing on query keys, query pagination (`.paginate()`), and using PyFlow connection pooling, search queries resolve under 5 milliseconds.

### Q3: Is PyFlow suitable for large NGO/Hospital Patient Tracking systems?
**Answer:** Absolutely. PostgreSQL/MySQL JSONB supports dynamic medical test tables, and RBAC permissions isolate sensitive health logs. Atomic transactions ensure no corrupted/partial medical files are ever committed.

### Q4: How does PyFlow prevent stock overselling in E-commerce ERPs?
**Answer:** PyFlow transaction locks block concurrency anomalies when the last item in stock is purchased. Orders, stock updates, and accounts ledger entries run in a single atomic database context.

### Q5: What is the 20-year compatibility and future of this custom framework?
**Answer:** Because PyFlow depends heavily on Python's native standard library modules, it suffers very little dependency rot. Over 170+ unit tests safeguard codebase integrity against deprecations, and standard MVC folders make onboarding new developers easy.

### Q6: What is the purpose of the Money class in `decimal_math.py`?
**Answer:** Computers suffer from binary representation limitations in floating point math (e.g. `0.1 + 0.2` equals `0.30000000000000004 BDT`). The Money class wraps Python's Decimal module with `ROUND_HALF_UP` logic to keep financial records accurate to the decimal digit.

### Q7: How do I install and manage external libraries in PyFlow?
**Answer:** Use standard pip packaging tools to install new libraries and pin their exact version in the `requirements.txt` file. This ensures environment consistency across development and production servers.

### Q8: How do I configure mail server settings?
**Answer:** Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD` inside the `.env` file. The `core/mailer.py` module leverages Python's built-in `smtplib` to route transaction messages securely.

### Q9: How does the Queue Worker operate in the background?
**Answer:** PyFlow implements a DB-backed queue worker. Running `python queue_worker.py` via CLI loops through the jobs table and runs registered tasks asynchronously via threads, keeping the HTTP server responsive.

### Q10: Are there other cache drivers besides Redis?
**Answer:** Yes. PyFlow's `core/cache.py` supports multiple cache backends. Set `CACHE_DRIVER=file` inside `.env` to store cached outputs inside the `storage/cache/` directory if you don't have a running Redis server.

### Q11: What is the benefit of the Interactive CLI Assistant?
**Answer:** The root `cli.py` script provides developer utilities. It lets you scaffold controllers, generate ORM models, inspect registered routes, health-check environmental requirements, and run database seeds instantly.

### Q12: How does CSRF protection secure web forms?
**Answer:** A unique cryptographic token is generated for every user session. Using `{{ csrf_field() }}` appends a hidden token to forms. Middleware matches it against the session token to prevent unauthorized cross-site requests.

### Q13: How does PyFlow handle file and image uploads?
**Answer:** The `core/storage.py` library abstracts disk writes. It performs file extension verification, size validations, and unique renaming before storing uploads inside the `public/uploads/` directories.

### Q14: Why are Database Seeders and Factories useful?
**Answer:** Factories and Seeders allow populating mock records for test runs. Using loops, developers can generate thousands of users or products dynamically within seconds in local and testing environments.

### Q15: How are FastAPI and PyFlow routes isolated?
**Answer:** PyFlow uses a custom ASGI-to-WSGI gateway bridge. Requests under the `/api/*` paths bypass the WSGI core router and map directly to FastAPI endpoints for high-performance async processing.

### Q16: How do I disable debugging output for production?
**Answer:** Before pushing to production, set `APP_DEBUG=false` inside `.env`. This hides execution traceback screens from end users and automatically turns off the debug footer bar in your views.

### Q17: How do I add custom middleware to routes?
**Answer:** Create your middleware class inheriting `Middleware`, and register it inside `core/middleware.py`. Apply it to routes in `config/routes.py` by passing the middleware keyword inside route setups.

### Q18: What is the process to run cron tasks via Scheduler?
**Answer:** Register tasks inside `app/scheduler.py` using `Scheduler.call()`. Run the daemon using `python scheduler_runner.py` or bind it to your system's crontab config to loop every minute.

### Q19: How does PyFlow prevent SQL injection in raw queries?
**Answer:** PyFlow wraps prepared statements. Parameters must be passed as a separate tuple to `Database.execute()` using placeholders, which prevents raw SQL string concatenations.

### Q20: How do I run tests and increase coverage metrics?
**Answer:** Execute `python -m unittest discover -s tests` to run unit tests. Write assertions inside `tests/test_*.py` to verify both valid inputs and exception cases of your new modules.

### Q21: How do JWT and API Key dual-mode authentication work?
**Answer:** FastAPI endpoints accept two auth flows: JWT Bearer Tokens for frontend client sessions and secure SHA-256 hashed API Keys (`X-API-Key` header) for machine-to-machine integrations.

### Q22: What are the deployment guidelines for a Linux VPS or Cloud?
**Answer:** Deploy on Linux using Gunicorn with Uvicorn workers behind an Nginx reverse proxy. Nginx handles static file assets and SSL certificates, while Gunicorn acts as the ASGI process manager.

---

## বাংলা সংস্করণ (Bengali Version)

### ১. শুধু HTML ব্যবহার করলে ডাইনামিক পেজে কি কোনো সমস্যা হবে?
**উত্তর:** না, কোনো সমস্যা হবে না। PyFlow-র শক্তিশালী সার্ভার-সাইড টেমপ্লেট লুপ ও কন্ডিশনাল রেন্ডারিং হ্যান্ডেল করে। ফ্রন্টএন্ডে সামান্য Vanilla JS, Alpine.js বা HTMX ব্যবহার করে কোনো প্রকার জটিল ফ্রন্টএন্ড ফ্রেমওয়ার্ক (যেমন React/Vue) ছাড়াই পুরোপুরি ডাইনামিক পেইজ ও রিয়েল-টাইম রিপোর্ট তৈরি করা সম্ভব।

### ২. MySQL কি ২০ লক্ষ বা তার বেশি ডাটা সহজে হ্যান্ডেল করতে পারবে?
**উত্তর:** হ্যাঁ, ২০ লক্ষ বা ২ মিলিয়ন ডাটা MySQL-এর জন্য খুবই সাধারণ সংখ্যা। PyFlow-তে কলাম ইনডেক্সিং (Indexing), কুয়েরি পেজিনেশন (`.paginate()`), এবং থ্রেড-সেফ কানেকশন পুলিং ব্যবহার করার কারণে প্রতিটা কুয়েরি লোড হতে ১ থেকে ৫ মিলি-সেকেন্ডের বেশি সময় লাগবে না।

### ৩. এই ফ্রেমওয়ার্ক দিয়ে কি বড় এনজিও বা ডায়াবেটিস/হাইপারটেনশন রোগীর ডাটা ট্র্যাকিং কাজ করা যাবে?
**উত্তর:** হ্যাঁ। PostgreSQL/MySQL-এর JSONB ড্রাইভার সাপোর্ট থাকায় রোগীদের ডাইনামিক মেডিকেল রিপোর্ট সহজে সেভ করা যাবে। এছাড়া ডাটার গোপনীয়তা রক্ষায় বিল্ট-ইন রোল পারমিশন (RBAC) এবং নিরাপদ এন্ট্রি নিশ্চিত করতে `@atomic` ট্রানজেকশন ম্যানেজার থাকায় এটি অত্যন্ত নিরাপদ ও স্থিতিশীল।

### ৪. ই-কমার্স ইআরপি (E-Commerce ERP)-তে স্টক ওভারসেলিং কীভাবে ঠেকানো যাবে?
**উত্তর:** PyFlow-র নেস্টেড ট্রানজেকশন ব্লক ও database-level lock (`SELECT FOR UPDATE`) নিশ্চিত করে যে স্টকে থাকা শেষ প্রোডাক্টটি এক সেকেন্ডের ব্যবধানে একাধিক ব্যক্তি কিনতে পারবে না। অর্ডারের সাথে সাথে স্টক অ্যাডজাস্টমেন্ট ও লেজার পোস্টিং একই ট্রানজেকশন বাউন্ডারিতে কাজ করায় ডাটা অসঙ্গতির কোনো সুযোগ নেই।

### ৫. দীর্ঘ মেয়াদে (আগামী ২০ বছর) এই কাস্টম ফ্রেমওয়ার্কের ভবিষ্যৎ কেমন ও কী কী সমস্যা হতে পারে?
**উত্তর:** PyFlow মূলত পাইথনের স্ট্যান্ডার্ড লাইব্রেরি (stdlib) নির্ভর করায় এর 'ডিপেন্ডেন্সি ল্যাগ' নেই বললেই চলে, যা একে অত্যন্ত ফিউচার-প্রুফ করে তোলে। ১৭০টির বেশি ইউনিট টেস্ট যেকোনো পাইথন রানটাইম আপগ্রেডের রিগ্রেশন ঠেকাতে পারে। যেহেতু এটি সাধারণ লারাভেল/কোডইগনাইটারের এমভিসি ডিজাইন প্যাটার্ন মেনে চলে, তাই যেকোনো নতুন ডেভেলপারের পক্ষে কোড সহজে মেইনটেইন করা সম্ভব।

### ৬. core/decimal_math.py এ Money ক্লাস তৈরির মূল উদ্দেশ্য কী ছিল?
**উত্তর:** কম্পিউটারের ভাসমান সংখ্যা বা float ডাটা টাইপের অভ্যন্তরীণ বাইনারি সীমাবদ্ধতার কারণে ফিন্যান্সিয়াল হিসাবে কিছু পয়সার গরমিল দেখা দেয় (যেমন: `০.১ + ০.২ = ০.৩০০০০০০০০০০০০০৪ BDT`)। Money ক্লাস পাইথনের Decimal লাইব্রেরি এবং ROUND_HALF_UP নিয়ম ব্যবহার করে প্রতিটি অ্যাকাউন্টিং এবং বিলিং গণনা ১ পয়সা পর্যন্ত নির্ভুল রাখে।

### ৭. PyFlow-তে কীভাবে এক্সটার্নাল লাইব্রেরি ইন্সটল এবং মেইনটেইন করব?
**উত্তর:** নতুন কোনো থার্ড-পার্টি লাইব্রেরি যুক্ত করতে হলে pip install এর মাধ্যমে প্যাকেজটি নামিয়ে রুট ডিরেক্টরির `requirements.txt` ফাইলে এর নির্দিষ্ট সংস্করণ লক (pin) করে দিতে হবে। এর ফলে ভবিষ্যতে ভিন্ন কোনো হোস্টিং এনভায়রনমেন্টে প্রজেক্টটি ডেপ্লয় করার সময় ডিপেন্ডেন্সি সংস্করণ অসঙ্গতি এড়ানো যাবে।

### ৮. ইমেইল মেইলার কীভাবে কনফিগার করা যাবে?
**উত্তর:** মেইলার কনফিগার করতে আপনার .env ফাইলে মেইল হোস্ট সেটিংস আপডেট করুন। `core/mailer.py` ফাইলটি পাইথনের smtplib ব্যবহার করে এবং SMTP_HOST, SMTP_PORT, SMTP_USER এবং SMTP_PASSWORD ভ্যালুর সাহায্যে ইনভয়েস বা নোটিফিকেশন মেইল পাঠাতে সক্ষম।

### ৯. কিউ (Queue Manager) কীভাবে ব্যাকগ্রাউন্ডে কাজ করে?
**উত্তর:** PyFlow-তে কোনো ভারী মেমোরি ব্রোকার (যেমন: Celery বা Redis) ছাড়াই ডাটাবেজ ব্যাকড কিউ ওয়ার্কার তৈরি করা হয়েছে। CLI থেকে `python queue_worker.py` চালালে এটি ডাটাবেজের jobs টেবিল থেকে নতুন পেন্ডিং টাস্ক থ্রেডিংয়ের সাহায্যে প্রসেস করতে থাকে এবং মূল ওয়েব সার্ভারকে রিলিজ রাখে।

### ১০. ক্যাশিং এর জন্য কি রেডিস ছাড়াও অন্য কোনো ড্রাইভ ব্যবহার করা সম্ভব?
**উত্তর:** হ্যাঁ। `core/cache.py` এ মাল্টি-ড্রাইভার ক্যাশ ইঞ্জিন রয়েছে। আপনার সার্ভারে যদি Redis ইনস্টল না থাকে, তবে .env ফাইলে `CACHE_DRIVER=file` সেট করে ফাইল-ভিত্তিক ক্যাশিং করতে পারেন, যা ডাটাবেস ক্যাশিংয়ের তুলনায় অনেক দ্রুত।

### ১১. সিএলআই ব্যবহার করে কোড স্কাফোল্ডিং এর সুবিধা কী?
**উত্তর:** রুট ডিরেক্টরির `cli.py` ফাইলটি একটি ডেভেলপমেন্ট অ্যাসিস্ট্যান্ট হিসেবে কাজ করে। কমান্ড লাইনে ১ ক্লিক করেই মডেল বা কন্ট্রোলারের বেসিক স্ট্রাকচার স্কাফোল্ড করা, ডাটাবেস মাইগ্রেশন রান করা, এবং সিস্টেম হেলথ ডায়াগনস্টিকস চেক করা সম্ভব।

### ১২. CSRF প্রটেকশন ফর্মে কীভাবে কাজ করে?
**উত্তর:** প্রতিটি ব্যবহারকারীর সেশনে একটি সিকিউর ক্রিপ্টোগ্রাফিক CSRF টোকেন জেনারেট হয়। HTML ফর্মে `{{ csrf_field() }}` ব্যবহার করলে একটি হিডেন ইনপুট ফিল্ড যুক্ত হয়। ফর্মে সাবমিট করা টোকেন এবং সেশনের টোকেন না মিললে মিডলওয়্যার রিকোয়েস্ট ব্লক করে দেয়।

### ১৩. ফাইল ও ইমেজ আপলোড করার ক্ষেত্রে কোড স্ট্রাকচার কেমন?
**উত্তর:** PyFlow-র `core/storage.py` ফাইলে আপলোড ও স্টোরেজ হেল্পার রয়েছে। এর সাহায্যে ফাইল এক্সটেনশন সিকিউরিটি চেক, রেনাম করা, এবং ফাইলের আকার ভ্যালিডেট করে প্রজেক্টের `public/uploads` বা storage ডিরেক্টরিগুলোতে সহজে সেভ করা যায়।

### ১৪. ডাটাবেস সিডার ও ফ্যাক্টরির ব্যবহারিক প্রয়োজনীয়তা কী?
**উত্তর:** অ্যাপ্লিকেশন ডেভেলপমেন্টের শুরুর দিকে ডাটাবেজে টেস্ট বা ডামি ডাটার প্রয়োজন হয়। সিডার এবং ফ্যাক্টরি স্ক্রিপ্টের সাহায্যে লুপ চালিয়ে সেকেন্ডের মধ্যে হাজার হাজার ডামি ব্যবহারকারী, পণ্য বা ক্যাটাগরি ডাটাবেজে যুক্ত করে টেস্টিং করা সম্ভব।

### ১৫. FastAPI এর রাউট কীভাবে আলাদা করে এপিআই হিসেবে ম্যাপ করা হয়েছে?
**উত্তর:** PyFlow এ ASGI-to-WSGI মিডলওয়্যার ব্রিজ রয়েছে। এর ফলে ইউজার যখন ব্রাউজারে /api দিয়ে কোনো রিকোয়েস্ট করেন, তখন গেটওয়ে ব্রিজের মাধ্যমে রিকোয়েস্টটি সরাসরি FastAPI এ চলে যায় এবং মূল এমভিসি রাউটের সাথে কোনো সংঘর্ষ ঘটে না।

### ১৬. প্রোডাকশনে ডেবাকবার বা ডিবাগ মোড বন্ধ করার নিয়ম কী?
**উত্তর:** অ্যাপ্লিকেশন প্রোডাকশন বা সার্ভারে রিলিজ করার আগে আপনার .env ফাইলে `APP_DEBUG=false` করে দিন। এর ফলে কোড এরর হলে ব্রাউজারে বিস্তারিত ট্রেসব্যাক হাইড হয়ে যাবে এবং নিচের ডেভেলপার ডেবাকবার বা ফুটবার ডিবাগ প্যানেলটি স্বয়ংক্রিয়ভাবে মুছে যাবে।

### ১৭. কাস্টম মিডলওয়্যার কীভাবে যুক্ত করব?
**উত্তর:** কাস্টম মিডলওয়্যার ক্লাস তৈরি করে `core/middleware.py` ফাইলে রেজিস্টার করতে হবে। এরপর `config/routes.py` ফাইলে রাউট ডিক্লারেশনের সময় middleware প্যারমিটারে রেজিস্টার করা ক্লাসের নাম পাস করলেই তা কার্যকর হবে।

### ১৮. সিডিউলার বা ক্রন টাস্ক রান করানোর সঠিক পদ্ধতি কী?
**উত্তর:** প্রথমে `app/scheduler.py` ফাইলে `Scheduler.call()` ব্যবহার করে আপনার টাস্ক রেজিস্টার করুন। এরপর লিনাক্স বা সার্ভারের ক্রনজবে প্রতি মিনিটে `python scheduler_runner.py` কমান্ডটি কল করার নিয়ম সেট করে দিলেই সিডিউলার স্বয়ংক্রিয়ভাবে টাস্ক চালাবে।

### ১৯. কাস্টম SQL কুয়েরিতে ইনজেকশন ঠেকানোর মূল লজিক কী?
**উত্তর:** PyFlow-তে কোনো ভ্যালু সরাসরি SQL স্ট্রিংয়ের সাথে যুক্ত করতে দেয়া হয় না। placeholders (?) এবং প্যারামিটারাইজড কুয়েরি বাইন্ডিং ট্যাপল আকারে কানেকশন ড্রাইভারের `execute()` মেথডে পাঠানো হয়, যা ডাটাবেজ লেভেলে ইনজেকশন স্ক্রিপ্টিং ফিল্টার করে ফেলে।

### ২০. ইউনিট টেস্ট ও টেস্টিং লাইব্রেরির কভারেজ বাড়ানোর নিয়ম কী?
**উত্তর:** টেস্ট রান করতে `python -m unittest discover -s tests` কমান্ডটি ব্যবহার করুন। নতুন কোনো ফিচার যোগ করার সময় `tests/` ফোল্ডারে একটি নির্দিষ্ট `test_*.py` ফাইল লিখে ফিচার ক্লাসের মেথডগুলোর পজিティブ ও নেগেটিভ রেসপন্স যাচাই করার মাধ্যমে টেস্ট কভারেজ বাড়ানো যায়।

### ২১. JWT এবং API Key কীভাবে ডুয়াল মোডে কাজ করে?
**উত্তর:** FastAPI এন্ডপয়েন্টগুলো ডুয়াল অথেন্টিকেশন সমর্থন করে। কাস্টমার অ্যাপ থেকে রিকোয়েস্ট করার জন্য Bearer JWT টোকেন ব্যবহার করা যাবে, অথবা থার্ড-পার্টি সফটওয়্যারের সাথে বিটুবি কানেকশনের জন্য হেডার হিসেবে `X-API-Key` দিয়ে প্রজেক্টে ডাটা পাঠানো যাবে।

### ২২. প্রজেক্টটি লিনাক্স ভিপিএস (Linux VPS) বা ক্লাউডে হোস্ট করার গাইডলাইন কী?
**উত্তর:** প্রোডাকশন লিনাক্স ভিপিএস-এ প্রজেক্ট হোস্ট করতে Uvicorn বা Gunicorn (Uvicorn workers সহ) প্রসেস ম্যানেজার হিসেবে ব্যবহার করবেন। একে Nginx এর রিভার্স প্রক্সি দিয়ে বাইন্ড করতে হবে যাতে SSL সার্টিফিকেট এবং স্ট্যাটিক ফাইল হ্যান্ডেল করা সহজ হয়।
