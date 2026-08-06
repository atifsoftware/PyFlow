# PyFlow Enterprise Architecture Guide 🚀

PyFlow is a modular, extensible, and high-performance **Enterprise Application Platform** built on top of a Micro-Kernel Architecture. This guide documents the core subsystems introduced in the Enterprise updates.

---

## 📂 Directory Layout

The workspace architecture isolates core logic, business domains, and third-party extensions:

```text
pyflow/
│
├── app/                      # Core MVC Application (Default)
├── core/                     # Micro-Kernel Engine (Routing, DB, Queue, Container)
├── modules/                  # Business Domain Modules (ERP Features)
│   └── inventory/            # Example Inventory Module
│       ├── controllers/
│       ├── models/
│       ├── views/
│       ├── module.json       # Module Manifest
│       └── providers.py      # Module Service Provider
│
├── plugins/                  # Feature Extensions (Integrations)
├── packages/                 # Reusable Independent Libraries
├── database/                 # Database Migrations and Seeders
└── public/                   # WSGI Entry point
```

---

## ⚙️ Service Providers

Service Providers are the bootstrapper of modules and plugins. They define a uniform interface for resource registration and dynamic binding.

Inherit from `core.provider.ServiceProvider` and override these methods:

- `register()`: Bind classes or services to the IoC Container. (Executes first).
- `boot()`: Register routes, view namespaces, event listeners, or start background loops. (Executes after registration).

### Example Service Provider (`modules/inventory/providers.py`):

```python
from core.provider import ServiceProvider
import os

class InventoryServiceProvider(ServiceProvider):
    def register(self):
        # Register template view namespace (e.g. inventory::dashboard)
        views_dir = os.path.join(os.path.dirname(__file__), "views")
        self.app.view_engine.register_namespace("inventory", views_dir)

    def boot(self):
        # Bind module controller actions to the routing tables
        router = self.app.router
        from core.controller import action
        from modules.inventory.controllers.inventory_controller import InventoryController
        
        router.get("/inventory", action(InventoryController, "index"))
```

---

## 🔎 Module & Plugin Auto-Discovery (Registry)

PyFlow dynamically scans directories during boot, looking for `module.json` or `plugin.json` manifests. If `"enabled": true` is specified, it registers and executes its providers.

### Manifest Schema (`module.json` / `plugin.json`):

```json
{
    "name": "Inventory",
    "version": "1.0.0",
    "enabled": true,
    "providers": [
        "modules.inventory.providers.InventoryServiceProvider"
    ]
}
```

---

## 💉 Dependency Injection (IoC Container)

PyFlow includes an **Inversion of Control (IoC) Container** (`core.container.Container`) supporting singleton bindings and recursive reflection-based autowiring.

### Bindings:

```python
# Bind concrete implementation
app.container.bind(DBService)

# Bind as a singleton
app.container.singleton(PaymentGateway)
```

### Controller Constructor Autowiring:

Request context parameters (`request`, `session`, `view_engine`) are matched thread-safely by name or type annotation, while other service classes are automatically resolved recursively from the container.

```python
class InventoryController(Controller):
    def __init__(self, request, session, view_engine, payment: PaymentGateway):
        super().__init__(request, session, view_engine)
        self.payment = payment

    def index(self):
        # Autowired PaymentGateway is fully resolved and injected
        status = self.payment.pay()
        return self.view("inventory::dashboard", {"status": status})
```

---

## 📡 Event Dispatcher

The Event system (`core.event.Event`) supports decoupled, thread-safe asynchronous and synchronous event listener triggers.

```python
from core.event import Event

# 1. Listen for an event
Event.listen("UserCreated", lambda user: print(f"Welcome {user.name}!"))

# 2. Fire the event
Event.fire("UserCreated", user_instance)
```

---

## 🪝 Hook System (Actions & Filters)

WordPress-style hook managers (`core.hook.Hook`) allow executing side effects (Actions) and mutating values in a pipeline (Filters) sorted by priority (default `10`, lower priorities execute first).

### Action Hooks (Side Effects):

```python
from core.hook import Hook

# Register action callback
Hook.add_action("before_login", lambda req: log_ip(req), priority=5)

# Trigger action hook
Hook.action("before_login", request)
```

### Filter Hooks (Value Mutation Chaining):

```python
from core.hook import Hook

# Register filter callbacks
Hook.add_filter("invoice_amount", lambda val: val - 10, priority=5)   # Discount
Hook.add_filter("invoice_amount", lambda val: val * 1.15, priority=10) # 15% VAT

# Trigger filter hook (mutates 100 -> (100 - 10) * 1.15 = 103.5)
total = Hook.filter("invoice_amount", 100)
```

---

## 🛠️ CLI Code Generators

CLI command arguments allow generating boilerplate modules, plugins, services, events, listeners, or middleware directly from the terminal.

```bash
# Generate Plugins & Modules
python cli.py make:plugin <name>
python cli.py make:module <name>

# Generate Core Subsystems
python cli.py make:package <name>
python cli.py make:service <name>
python cli.py make:event <name>
python cli.py make:listener <name>
python cli.py make:middleware <name>
```
