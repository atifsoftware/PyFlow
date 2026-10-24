# PyFlow Framework - নতুন ফিচারসমূহ

## ✅ যুক্ত করা হয়েছে

### ১. API Rate Limiting (রেট লিমিটিং)
**অবস্থান:** `app/middlewares/rate_limiter.py`

একটি আইপি থেকে নির্দিষ্ট সময়ে কতবার রিকোয়েস্ট যাবে তা সীমাবদ্ধ করে।

**ব্যবহার:**
```python
from app.middlewares.rate_limiter import rate_limit_middleware

# সব রাউটে রেট লিমিট প্রয়োগ (১ মিনিটে ১০০ রিকোয়েস্ট)
router.use(rate_limit_middleware(max_requests=100, window_seconds=60))

# অথবা নির্দিষ্ট গ্রুপে (১ মিনিটে ৫০ রিকোয়েস্ট)
with router.group(prefix="/api", middleware=[rate_limit_middleware(max_requests=50)]):
    # API রাউটসমূহ
    pass
```

**সুবিধা:**
- DDoS এটাক থেকে রক্ষা পাবে
- API অপব্যবহার রোধ হবে
- সার্ভার লোড ব্যালেন্স হবে

---

### ২. Flash Message System (ফ্ল্যাশ মেসেজ)
**অবস্থান:** `core/session.py` (ইতিমধ্যে বিদ্যমান)

এক রিকোয়েস্ট থেকে অন্য রিকোয়েস্টে মেসেজ নিয়ে যাওয়ার সুবিধা।

**ব্যবহার:**
```python
# Controller এ সেট করা
def store(request, session):
    # ডেটা সেভ করার পর
    session.flash('success', 'Data saved successfully!')
    return Response.redirect('/dashboard')

def update(request, session):
    session.flash('error', 'Update failed. Please try again.')
    return Response.redirect('/settings')

# Template এ দেখানো (Jinja2)
{% if session.get_flash('success') %}
    <div class="alert alert-success">
        {{ session.get_flash('success') }}
    </div>
{% endif %}

{% if session.get_flash('error') %}
    <div class="alert alert-danger">
        {{ session.get_flash('error') }}
    </div>
{% endif %}

# অথবা সব ফ্ল্যাশ মেসেজ একসাথে
{% for type, message in session.all_flash().items() %}
    <div class="alert alert-{{ type }}">{{ message }}</div>
{% endfor %}
```

**সুবিধা:**
- ইউজার এক্সপেরিয়েন্স অনেক ভালো হবে
- Success/Error মেসেজ অটোমেটিক ডিলিট হয়ে যাবে
- মাল্টিপল মেসেজ সাপোর্ট করে

---

### ৩. Auto API Documentation (Swagger/OpenAPI)
**অবস্থান:** `app/routes/api.py` এবং `app/routes/web.py`

অটোমেটিক API ডকুমেন্টেশন জেনারেট করে।

**এন্ডপয়েন্টসমূহ:**
- `GET /api/docs` - OpenAPI 3.0 JSON স্কিমা
- `GET /api-docs` - সুন্দর HTML UI (Swagger-like)

**JSON স্কিমা এক্সেস:**
```bash
curl http://localhost:8000/api/docs
```

**HTML UI এক্সেস:**
```
http://localhost:8000/api-docs
```

**সুবিধা:**
- ডেভেলপাররা সহজে API বুঝতে পারবে
- Test করতে সুবিধা হবে
- Auto-generated এবং up-to-date

### ৪. Soft Deletes (সফট ডিলিট ও রিস্টোর)
**অবস্থান:** `core/model.py` এবং `core/query_builder.py`

ERP এবং এন্টারপ্রাইজ সিস্টেমে ডাটা সরাসরি মুছে না ফেলে `deleted_at` টাইমস্ট্যাম্প সেট করে সংরক্ষণ করা।

**ব্যবহার:**
```python
from core.model import Model

class Invoice(Model):
    table = "invoices"
    fillable = ["invoice_number", "customer_id", "total_amount", "deleted_at"]
    soft_deletes = True  # সফট ডিলিট সক্রিয় করে

# ১. সাধারণ ডিলিট (সফট ডিলিট হবে, deleted_at = NOW)
invoice = Invoice.find(10)
invoice.delete()
print(invoice.trashed()) # True

# ২. সাধারণ কুয়েরি স্বয়ংক্রিয়ভাবে ডিলিট হওয়া রেকর্ড বাদ দেবে
active_invoices = Invoice.all() # WHERE deleted_at IS NULL

# ৩. ডিলিট হওয়া রেকর্ড সহ আনা
all_invoices = Invoice.with_trashed().get()

# ৪. শুধুমাত্র ডিলিট হওয়া রেকর্ড আনা
trashed = Invoice.only_trashed().get()

# ৫. রিস্টোর করা (deleted_at = None)
invoice.restore()

# ৬. ডাটাবেজ থেকে স্থায়ীভাবে মুছে ফেলা
invoice.force_delete()
```

---

### ৫. Audit Trail ও মডেল অবজারভার (অডিট চেঞ্জ লগ)
**অবস্থান:** `core/audit.py` এবং `core/model.py`

মডেলে কোনো পরিবর্তন হলে কে পরিবর্তন করলো, কোন IP থেকে, আগের মান ও পরের মান কী ছিল তা স্বয়ংক্রিয়ভাবে অডিট লগে সেভ করে।

**ব্যবহার:**
```python
from core.model import Model

class Product(Model):
    table = "products"
    fillable = ["name", "price", "stock"]
    audit_trail = True # অডিট লগিং চালু করে

# মডেল তৈরি বা আপডেট হলে স্বয়ংক্রিয়ভাবে audit_logs টেবিলে রেকর্ড হবে
product = Product.create({"name": "Laptop", "price": 1200, "stock": 10})

# আপডেট করা (Active Record save)
product.stock = 15
product.save()

# এই প্রোডাক্টের সব পরিবর্তন হিস্টোরি দেখা
history = product.audit_logs()
for log in history:
    print(log.event, log.diff()) # e.g. updated {'stock': (10, 15)}
```

---

### ৬. Form Request & DTO ভ্যালিডেশন লেয়ার
**অবস্থান:** `core/form_request.py` এবং `core/controller.py`

কন্ট্রোলারের ভেতর বড় বড় ভ্যালিডেশন কোড না লিখে ডেডিকেটেড রিকোয়েস্ট ক্লাস তৈরি এবং টাইপ-হিন্ট দিয়ে কন্ট্রোলার মেথডে অটো-ইনজেক্ট করা।

**ব্যবহার:**
```python
# app/requests/store_customer_request.py
from core.form_request import FormRequest

class StoreCustomerRequest(FormRequest):
    def authorize(self) -> bool:
        return self.user() is not None # অথোরাইজেশন চেক

    def rules(self) -> dict:
        return {
            "name": "required|min:3",
            "email": "required|email",
            "credit_limit": "required|numeric",
        }

# app/controllers/customer_controller.py
from core.controller import Controller

class CustomerController(Controller):
    # মেথডে টাইপ-হিন্ট দিলেই ফ্রেমওয়ার্ক স্বয়ংক্রিয়ভাবে ভ্যালিডেশন চেক করবে
    def store(self, form: StoreCustomerRequest):
        # ভ্যালিডেশন ফেইল হলে মেথড কলই হবে না (অটোমেটিক ৪২২ রেসপন্স যাবে)
        data = form.validated() # শুধুমাত্র রুলসে ডিফাইন করা নিরাপদ ফিল্ড
        customer = Customer.create(data)
        return self.json({"message": "Customer created", "id": customer.id}, status=201)
```

---

### ৭. Developer DX: Interactive Tinker Shell & Maintenance Mode
**অবস্থান:** `cli.py`

**১. Interactive REPL Shell (Tinker):**
```bash
python cli.py tinker
```
ফ্রেমওয়ার্কের সমস্ত মডেল এবং ডাটাবেজ টার্মিনালে লোড করে সরাসরি লাইভ কোড রান ও টেস্ট করার সুবিধা।

**২. Maintenance Mode (ডাউন ও আপ):**
```bash
# সাইট মেইনটেনেন্সে নেওয়া (নির্দিষ্ট বাইপাস সিক্রেট কি সহ)
python cli.py down --secret=adminpass --message="We are upgrading our servers"

# অ্যাডমিন বাইপাস URL:
# http://localhost:8000/?secret=adminpass

# সাইট পুনরায় লাইভ করা:
python cli.py up
```

**৩. FormRequest জেনারেটর:**
```bash
python cli.py make:request StoreInvoiceRequest
```

---

## 📊 টেস্ট রেজাল্ট

✅ **Rate Limiter:** ৫টি রিকোয়েস্টের পর ৬ষ্ঠ রিকোয়েস্ট ব্লক হয়েছে  
✅ **Flash Messages:** Success এবং Error মেসেজ সঠিকভাবে কাজ করছে  
✅ **API Docs:** `/api/docs` এবং `/api-docs` রাউট যুক্ত হয়েছে  
✅ **মোট রাউট:** ৩৬টি (আগের ৩৪টি + ২টি নতুন)  

---

## 🔜 পরবর্তী করণীয়

1. **Rate Limiter কে Redis-ভিত্তিক করা** (মাল্টি-সার্ভার এনভায়রনমেন্টের জন্য)
2. **API Documentation এ Swagger UI ইন্টিগ্রেশন** (আরও ইন্টারঅ্যাক্টিভ করার জন্য)
3. **Flash Message Helper Functions** (Template এ আরও সহজে ব্যবহারের জন্য)
4. **Rate Limit Configuration** (.env ফাইল থেকে কনফিগার করার জন্য)

---

## 📝 উদাহরণ

### Rate Limiting with Custom Settings
```python
# main.py বা routes ফাইলে
from app.middlewares.rate_limiter import rate_limit_middleware

# API গ্রুপে স্ট্রিক্ট লিমিট
api_middleware = [
    api_auth_middleware,
    rate_limit_middleware(max_requests=30, window_seconds=60)  # ১ মিনিটে ৩০ রিকোয়েস্ট
]

with router.group(prefix="/api/v1", middleware=api_middleware):
    # protected routes
    pass
```

### Flash Message in Controller
```python
# app/controllers/user_controller.py
from core.controller import action

@action
def create(request, session, db):
    try:
        # user creation logic
        session.flash('success', f"User {name} created successfully!")
        return Response.redirect('/users')
    except Exception as e:
        session.flash('error', str(e))
        return Response.redirect('/users/create')
```

### Access API Docs
```bash
# JSON Schema
curl http://localhost:8000/api/docs | jq

# Visit HTML UI
open http://localhost:8000/api-docs
```
