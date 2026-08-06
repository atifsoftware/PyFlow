# PyFlow Framework Installation Guide 🛠️

[বাংলা গাইড নিচে দেওয়া হয়েছে]

Welcome to the installation and deployment guide for the **PyFlow** framework. This guide covers how to set up PyFlow for local development, deploy it on cPanel Shared Hosting, or set it up on a Linux VPS.

---

## 📋 Prerequisites
* Python >= 3.9
* pip (Python package installer)
* SQLite, MySQL, or PostgreSQL Database

---

## 💻 1. Local Development Setup (লোকাল সেটআপ)

Follow these steps to set up the project on your local machine:

### Step 1: Clone the Repository
```bash
git clone https://github.com/atifsoftware/PyFlow.git
cd PyFlow
```

### Step 2: Create a Virtual Environment
It is highly recommended to run the app in a virtual environment:
* **On Windows:**
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
* **On macOS/Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### Step 3: Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure the Environment File
Copy the example environment file and configure your settings:
```bash
cp .env.example .env
```
Open `.env` in your editor. For local setup, you can use `sqlite` (default):
```ini
DB_DRIVER=sqlite
DB_NAME=storage/database.sqlite
```
Or configure MySQL if you have it running locally:
```ini
DB_DRIVER=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=your_local_db
DB_USER=your_db_user
DB_PASSWORD=your_db_password
```

### Step 5: Run Database Migrations
Create the database tables and seed them with default admin data:
```bash
python migrate.py
```
*(Optional: Use `python migrate.py --refresh` if you want to drop all tables and seed a completely fresh database).*

### Step 6: Start the Development Server
```bash
python run.py
```
The application will run on **http://127.0.0.1:8000**.
* Open **http://127.0.0.1:8000/login** to access the Admin Panel.
* Default Admin Credentials:
  * **Email:** `admin@pyflow.com`
  * **Password:** `admin123`

---

## 🌐 2. cPanel Shared Hosting Deployment (সিপ্যানেল ডেপ্লয়মেন্ট)

cPanel uses **Phusion Passenger** to run Python WSGI apps. Follow these steps for cPanel deployment:

### Step 1: Upload the Project
Upload the project files to your cPanel directory (e.g., `/home/username/pyflow.yourdomain.com/`).
* **Do NOT upload** `.git/`, `venv/`, `storage/database.sqlite`, or local logs.
* Make sure `passenger_wsgi.py` is present in the root folder.

### Step 2: Create a MySQL Database in cPanel
1. Go to **MySQL Database Wizard** in cPanel.
2. Create a database (e.g., `username_pyflow_db`).
3. Create a database user (e.g., `username_pyflow_user`) and give it a strong password.
4. **Important:** Add the user to the database and check **"ALL PRIVILEGES"**.

### Step 3: Create the Python Application in cPanel
1. Go to **Setup Python App** in your cPanel dashboard.
2. Click **Create Application**.
3. Fill in the fields:
   * **Python Version:** Select Python `3.9` or higher.
   * **Application root:** The path to your project folder (e.g., `pyflow.yourdomain.com`).
   * **Application URL:** Select your subdomain/domain.
   * **Application startup file:** Set this to `passenger_wsgi.py`.
   * **Application Entry point:** Leave empty (defaults to `application`).
4. Click **Create**.

### Step 4: Configure the `.env` File
Create a `.env` file in the root folder of your project on the server and enter your credentials:
```ini
APP_NAME="PyFlow Production"
APP_VERSION=v3.0.0
APP_DEBUG=false
APP_URL=https://yourdomain.com

DB_DRIVER=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=username_pyflow_db
DB_USER=username_pyflow_user
DB_PASSWORD=your_strong_password
DB_POOL_SIZE=5
DB_TIMEZONE=+06:00

SESSION_DIR=storage/sessions
VIEWS_DIR=app/views
LOG_FILE=storage/logs/app.log
```

### Step 5: Install Dependencies
1. Copy the virtual environment path command shown at the top of the **Setup Python App** page.
2. Log into SSH terminal (if enabled) or run the command via the cPanel Terminal.
3. Once the environment is activated, run:
   ```bash
   pip install -r requirements.txt
   ```
*(Alternative: You can use the **Configuration files** section inside cPanel's Setup Python App UI to add `requirements.txt` and click **Run Pip Install**).*

### Step 6: Run Migrations on the Server
You can run migrations by accessing the server terminal:
```bash
python migrate.py
```

### Step 7: Restart the Application
In cPanel **Setup Python App**, click the **RESTART** button next to your application. Open your website to verify.

---

## ⚡ 3. Linux VPS Deployment (ভিপিএস ডেপ্লয়মেন্ট)

For production Linux servers (Ubuntu/Debian), run Gunicorn behind an Nginx reverse proxy.

### Step 1: Install System Packages
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx mysql-server git -y
```

### Step 2: Configure Systemd Service for PyFlow
Create a systemd service file:
```bash
sudo nano /etc/systemd/system/pyflow.service
```
Paste the following configurations (adjust paths and user settings):
```ini
[Unit]
Description=PyFlow ASGI Web Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/pyflow
Environment="PATH=/var/www/pyflow/venv/bin"
ExecStart=/var/www/pyflow/venv/bin/gunicorn core.asgi_bridge:application -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl enable pyflow
sudo systemctl start pyflow
```

### Step 3: Configure Nginx as a Reverse Proxy
Create an Nginx configuration file:
```bash
sudo nano /etc/nginx/sites-available/pyflow
```
Paste configuration:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location /static/ {
        alias /var/www/pyflow/public/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
Link and reload Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/pyflow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---
---

# PyFlow ফ্রেমওয়ার্ক ইনস্টলেশন গাইড 🛠️

PyFlow ফ্রেমওয়ার্ক সেটআপ ও ডেপ্লয়মেন্ট নির্দেশিকায় সমাদর। এই গাইডলাইনটি আপনাকে লোকাল কম্পিউটার, সিপ্যানেল (cPanel) শেয়ার্ড হোস্টিং এবং লিনাক্স ভিপিএস (Linux VPS)-এ প্রজেক্ট রান করাতে সাহায্য করবে।

---

## 💻 ১. লোকাল কম্পিউটার সেটআপ (Local Setup)

### ধাপ ১: রিপোজিটরি ক্লোন করুন
```bash
git clone https://github.com/atifsoftware/PyFlow.git
cd PyFlow
```

### ধাপ ২: ভার্চুয়াল এনভায়রনমেন্ট তৈরি করুন
* **Windows এর জন্য:**
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
* **Mac/Linux এর জন্য:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### ধাপ ৩: ডিপেন্ডেন্সি ইনস্টল করুন
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### ধাপ ৪: এনভায়রনমেন্ট (.env) ফাইল সেট করুন
```bash
cp .env.example .env
```
আপনার টেক্সট এডিটরে `.env` ফাইলটি খুলুন। লোকাল সেটআপের জন্য ডিক্লেয়ার করা ডিফল্ট SQLite ড্রাইভারটি ব্যবহার করতে পারেন:
```ini
DB_DRIVER=sqlite
DB_NAME=storage/database.sqlite
```

### ধাপ ৫: ডাটাবেস মাইগ্রেশন রান করুন
```bash
python migrate.py
```
*(নোট: ডাটাবেজ ক্লিয়ার করে নতুন করে ডাটা রি-সিড করতে `python migrate.py --refresh` রান করুন)*।

### ধাপ ৬: লোকাল সার্ভার রান করুন
```bash
python run.py
```
সার্ভারটি চালু হবে এবং ব্রাউজারে **http://127.0.0.1:8000** ঠিকানায় পেজটি দেখতে পাবেন।
* অ্যাডমিন প্যানেল লগইন লিংক: **http://127.0.0.1:8000/login**
* ডিফল্ট অ্যাডমিন ক্রেডেনশিয়াল:
  * **ইমেইল:** `admin@pyflow.com`
  * **পাসওয়ার্ড:** `admin123`

---

## 🌐 ২. cPanel শেয়ার্ড হোস্টিংয়ে ডেপ্লয়মেন্ট (cPanel Deployment)

সিপ্যানেলে পাইথন চালানোর জন্য **Phusion Passenger** মেকানিজম ব্যবহার করা হয়। ডেপ্লয়মেন্ট সম্পূর্ণ করতে নিচের ধাপগুলো অনুসরণ করুন:

### ধাপ ১: ফাইল আপলোড করুন
ফাইল ম্যানেজার ব্যবহার করে প্রজেক্টের সব ফাইল জিপ আকারে আপনার সিপ্যানেল ডিরেক্টরিতে (যেমন: `/home/username/pyflow.yourdomain.com/`) আপলোড করে এক্সট্র্যাক্ট করুন।
* **যেগুলো আপলোড করার প্রয়োজন নেই:** `.git/`, `venv/`, `storage/database.sqlite`, অথবা লোকাল টেস্ট লগসমূহ।
* রুট ফোল্ডারে যেন `passenger_wsgi.py` ফাইলটি থাকে তা নিশ্চিত করুন।

### ধাপ ২: cPanel-এ MySQL ডাটাবেজ তৈরি করুন
1. cPanel থেকে **MySQL Database Wizard**-এ যান।
2. নতুন ডাটাবেজ তৈরি করুন (যেমন: `username_pyflow_db`)।
3. ডাটাবেজ ইউজার তৈরি করে একটি পাসওয়ার্ড দিন।
4. **গুরুত্বপূর্ণ:** ইউজারটিকে ডাটাবেজের সাথে যুক্ত করার সময় অবশ্যই **"ALL PRIVILEGES"** অপশনটি টিক দিন।

### ধাপ ৩: cPanel-এ Python App কনফিগার করুন
1. cPanel-এর সার্চ বক্সে **Setup Python App** লিখে সেটি ওপেন করুন।
2. **Create Application** বাটনে ক্লিক করুন।
3. নিচের ফিল্ডগুলো এভাবে ফিলাপ করুন:
   * **Python Version:** Python `3.9` বা তার বেশি সিলেক্ট করুন।
   * **Application root:** আপনার প্রজেক্ট আপলোড ফোল্ডারের নাম (যেমন: `pyflow.yourdomain.com`)।
   * **Application URL:** আপনার নির্দিষ্ট ডোমেইন/সাবডোমেইনটি সিলেক্ট করুন।
   * **Application startup file:** এটি অবশ্যই লিখবেন: `passenger_wsgi.py`।
   * **Application Entry point:** এটি ফাঁকা রাখুন (ডিফল্ট `application` সেট হবে)।
4. নিচে থাকা **Create** বাটনে ক্লিক করুন।

### ধাপ ৪: সার্ভারে `.env` ফাইল আপডেট করুন
সার্ভারে থাকা প্রজেক্টের রুট ডিরেক্টরিতে একটি নতুন `.env` ফাইল তৈরি করুন এবং আপনার ডাটাবেজ ক্রেডেনশিয়াল দিন:
```ini
APP_NAME="PyFlow Production"
APP_VERSION=v3.0.0
APP_DEBUG=false
APP_URL=https://yourdomain.com

DB_DRIVER=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=username_pyflow_db
DB_USER=username_pyflow_user
DB_PASSWORD=your_strong_password
DB_POOL_SIZE=5
DB_TIMEZONE=+06:00

SESSION_DIR=storage/sessions
VIEWS_DIR=app/views
LOG_FILE=storage/logs/app.log
```

### ধাপ ৫: সার্ভারে ডিপেন্ডেন্সি ও লাইব্রেরি ইনস্টল করুন
1. **Setup Python App** পেজের ঠিক উপরে একটি ভার্চুয়াল এনভায়রনমেন্ট পাথ কমান্ড (e.g., `source /home/.../bin/activate`) দেখতে পাবেন, সেটি কপি করুন।
2. সিপ্যানেল **Terminal** ওপেন করে কমান্ডটি পেস্ট করে এন্টার দিন।
3. ভার্চুয়াল এনভায়রনমেন্ট সক্রিয় হলে রান করুন:
   ```bash
   pip install -r requirements.txt
   ```
*(বিকল্প পদ্ধতি: Setup Python App ইন্টারফেসের **Configuration files** অপশনে `requirements.txt` ফাইলটি টাইপ করে অ্যাড করুন এবং **Run Pip Install** বাটনে ক্লিক করুন)।*

### ধাপ ৬: সার্ভারে ডাটাবেস মাইগ্রেশন রান করুন
টার্মিনাল থেকে প্রজেক্ট ফোল্ডারে এসে রান করুন:
```bash
python migrate.py
```

### ধাপ ৭: অ্যাপ্লিকেশন রিস্টার্ট করুন
সবশেষে **Setup Python App** পেজে গিয়ে অ্যাপটির নামের পাশে থাকা **`RESTART`** বাটনে ক্লিক করুন। আপনার ওয়েবসাইটটি ব্রাউজারে চালু হয়ে যাবে!

---

## ⚡ ৩. লিনাক্স ভিপিএস ডেপ্লয়মেন্ট (Linux VPS Deployment)

ভিপিএস বা ক্লাউড সার্ভারে Gunicorn প্রসেস ম্যানেজার এবং Nginx রিভার্স প্রক্সি ব্যবহার করে প্রজেক্ট লাইভ করা হয়।

### ধাপ ১: সিস্টেম প্যাকেজসমূহ ইনস্টল করুন
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx mysql-server git -y
```

### ধাপ ২: PyFlow-এর জন্য Systemd সার্ভিস তৈরি করুন
একটি সার্ভিস ফাইল ক্রিয়েট করুন:
```bash
sudo nano /etc/systemd/system/pyflow.service
```
নিচের কনফিগারেশনটি পেস্ট করুন (আপনার প্রজেক্টের পাথ অনুযায়ী পরিবর্তন করুন):
```ini
[Unit]
Description=PyFlow ASGI Web Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/pyflow
Environment="PATH=/var/www/pyflow/venv/bin"
ExecStart=/var/www/pyflow/venv/bin/gunicorn core.asgi_bridge:application -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000

[Install]
WantedBy=multi-user.target
```
সার্ভিসটি চালু ও এনাবেল করুন:
```bash
sudo systemctl enable pyflow
sudo systemctl start pyflow
```

### ধাপ ৩: Nginx রিভার্স প্রক্সি কনফিগার করুন
Nginx কনফিগারেশন তৈরি করুন:
```bash
sudo nano /etc/nginx/sites-available/pyflow
```
কনফিগারেশন পেস্ট করুন:
```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location /static/ {
        alias /var/www/pyflow/public/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
কনফিগারেশন ফাইলটি এনাবেল করে Nginx রিলোড দিন:
```bash
sudo ln -s /etc/nginx/sites-available/pyflow /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```
