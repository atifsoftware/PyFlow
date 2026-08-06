"""
PyFlow CLI Tool
===============
An interactive, menu-driven CLI utility for managing PyFlow framework.
"""

import os
import sys
import shutil
import platform
import subprocess

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config.config import get_config
from core.database import Database
from config.routes import build_router

# Colors
C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_RED = "\033[31m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_MAGENTA = "\033[35m"
C_CYAN = "\033[36m"
C_WHITE = "\033[37m"

def color(text, col):
    return f"{col}{text}{C_RESET}"

def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")

def print_header():
    clear_screen()
    print(color("╔════════════════════════════════════════════╗", C_CYAN))
    print(color("║       ⚡ PYFLOW CORE CLI ASSISTANT ⚡       ║", C_CYAN + C_BOLD))
    print(color("║       Framework Development Kit            ║", C_CYAN))
    print(color("╚════════════════════════════════════════════╝", C_CYAN))
    print()

def pause():
    input(color("\nPress Enter to continue...", C_CYAN))
    print_header()

class PyFlowCLI:
    def __init__(self):
        self.config = get_config()
        Database.init(self.config)

    def run(self):
        print_header()
        while True:
            print(color("=== MAIN MENU ===", C_BOLD))
            print(f"1. {color('View Registered Routes', C_CYAN)}")
            print(f"2. {color('View Database Tables', C_WHITE)}")
            print(f"3. {color('Database Summary Report', C_YELLOW)}")
            print(f"4. {color('Generate Model File', C_GREEN)}")
            print(f"5. {color('Generate Controller File', C_GREEN)}")
            print(f"6. {color('System Health Check', C_BOLD)}")
            print(f"7. {color('Clear Logs & Temp Sessions', C_RED)}")
            print(f"8. {color('Run Database Migrations', C_MAGENTA)}")
            print(f"9. {color('Run Database Seeders', C_CYAN)}")
            print(f"10. {color('Run Queue Worker', C_MAGENTA)}")
            print(f"11. {color('Run Task Scheduler', C_CYAN)}")
            print(f"12. {color('Database Schema Sync Tool', C_MAGENTA)}")
            print(color("--- Code Generators ---", C_YELLOW))
            print(f"13. {color('make:migration — New Migration File', C_GREEN)}")
            print(f"14. {color('make:job — New Background Job', C_GREEN)}")
            print(f"15. {color('make:middleware — New Middleware', C_GREEN)}")
            print(f"16. {color('make:seeder — New Database Seeder', C_GREEN)}")
            print(f"17. {color('Run Tests — Unit Test Suite', C_CYAN)}")
            print(f"18. {color('Flush Cache — Clear All Cached Data', C_RED)}")
            print(f"0. {color('Exit', C_RED)}")
            print()

            choice = input(color("Select option: ", C_YELLOW)).strip()

            if choice == "1":
                self.view_routes()
            elif choice == "2":
                self.view_tables()
            elif choice == "3":
                self.db_summary()
            elif choice == "4":
                self.generate_model()
            elif choice == "5":
                self.generate_controller()
            elif choice == "6":
                self.health_check()
            elif choice == "7":
                self.clear_logs()
            elif choice == "8":
                self.run_migrations()
            elif choice == "9":
                self.run_seeders()
            elif choice == "10":
                self.run_queue_worker()
            elif choice == "11":
                self.run_scheduler()
            elif choice == "12":
                self.run_db_sync()
            elif choice == "13":
                self.make_migration()
            elif choice == "14":
                self.make_job()
            elif choice == "15":
                self.make_middleware()
            elif choice == "16":
                self.make_seeder()
            elif choice == "17":
                self.run_tests()
            elif choice == "18":
                self.flush_cache()
            elif choice == "0":
                print(color("\n✓ Goodbye from PyFlow!\n", C_GREEN))
                break
            else:
                print(color("✗ Invalid option! Try again.", C_RED))
                pause()

    def view_routes(self):
        print(color("\nRegistered Routes:\n", C_BOLD))
        router = build_router()
        
        # Header
        print(f"{'Method':<8} | {'Path':<45} | {'Handler':<40} | {'Name':<20} | Middleware")
        print("-" * 140)
        
        for route in router.routes:
            handler_str = route.handler.__name__ if hasattr(route.handler, '__name__') else str(route.handler)
            mw_str = ", ".join([mw.__name__ if hasattr(mw, '__name__') else str(mw) for mw in route.middleware]) if route.middleware else "None"
            print(f"{route.method:<8} | {route.raw_pattern:<45} | {handler_str:<40} | {str(route.name or ''):<20} | {mw_str}")
        
        pause()

    def view_tables(self):
        print(color("\nDatabase Tables:\n", C_BOLD))
        try:
            tables = self._get_tables()
            if not tables:
                print("কোনো টেবিল পাওয়া যায়নি।")
            else:
                for idx, table in enumerate(tables, 1):
                    print(f"{idx}. {table}")
        except Exception as e:
            print(color(f"Error fetching tables: {e}", C_RED))
        pause()

    def db_summary(self):
        print(color("\nDatabase Record Summary:\n", C_BOLD))
        try:
            tables = self._get_tables()
            if not tables:
                print("কোনো টেবিল পাওয়া যায়নি।")
            else:
                print(f"{'Table Name':<30} | Record Count")
                print("-" * 45)
                for table in tables:
                    try:
                        cursor = Database.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                        row = cursor.fetchone()
                        count = row[0] if isinstance(row, tuple) else row.get("cnt", 0) if isinstance(row, dict) else row["cnt"]
                        print(f"{table:<30} | {count}")
                    except Exception:
                        print(f"{table:<30} | [Error reading]")
        except Exception as e:
            print(color(f"Error connecting to database: {e}", C_RED))
        pause()

    def generate_model(self):
        print(color("\nGenerate Model:\n", C_BOLD))
        name = input(color("Enter model name (e.g. Product): ", C_YELLOW)).strip()
        if not name:
            print("Model name required!")
            pause()
            return
        
        table = input(color("Enter database table name (e.g. products): ", C_YELLOW)).strip()
        if not table:
            table = name.lower() + "s"
            
        model_name = name[0].upper() + name[1:]
        file_name = f"{name.lower()}_model.py"
        file_path = os.path.join(PROJECT_ROOT, "app", "models", file_name)
        
        if os.path.exists(file_path):
            print(color(f"✗ File {file_name} already exists!", C_RED))
            pause()
            return

        content = f'''"""
app/models/{file_name}
"""

from core.model import Model


class {model_name}(Model):
    table = "{table}"
    fillable = ["name", "created_at", "updated_at"]
'''
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(color(f"✓ Model successfully created at app/models/{file_name}!", C_GREEN))
        except Exception as e:
            print(color(f"✗ Error: {e}", C_RED))
        pause()

    def generate_controller(self):
        print(color("\nGenerate Controller:\n", C_BOLD))
        name = input(color("Enter controller prefix name (e.g. Product): ", C_YELLOW)).strip()
        if not name:
            print("Controller name required!")
            pause()
            return

        name_clean = name[0].upper() + name[1:]
        controller_name = f"{name_clean}Controller"
        file_name = f"{name.lower()}_controller.py"
        file_path = os.path.join(PROJECT_ROOT, "app", "controllers", file_name)

        if os.path.exists(file_path):
            print(color(f"✗ File {file_name} already exists!", C_RED))
            pause()
            return

        content = f'''"""
app/controllers/{file_name}
"""

from core.controller import Controller


class {controller_name}(Controller):
    def index(self):
        return self.view("{name.lower()}.index", {{}})
'''
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(color(f"✓ Controller successfully created at app/controllers/{file_name}!", C_GREEN))
        except Exception as e:
            print(color(f"✗ Error: {e}", C_RED))
        pause()

    def health_check(self):
        print(color("\nPyFlow System Health Check:\n", C_BOLD))
        
        # 1. Python Version
        py_ver = sys.version.split()[0]
        py_ok = sys.version_info >= (3, 9)
        self._print_check("Python Version (>= 3.9)", py_ver, py_ok)
        
        # 2. Key Directories Writable
        dirs = ["storage/logs", "storage/sessions"]
        for d in dirs:
            full_path = os.path.join(PROJECT_ROOT, d)
            os.makedirs(full_path, exist_ok=True)
            writable = os.access(full_path, os.W_OK)
            self._print_check(f"Writable Directory: {d}", "Yes" if writable else "No", writable)
            
        # 3. Environment Config
        env_exists = os.path.exists(os.path.join(PROJECT_ROOT, ".env"))
        self._print_check(".env Config File", "Exists" if env_exists else "Missing", env_exists)
        
        # 4. Database Connection
        db_connected = False
        db_msg = "Unknown"
        try:
            Database.execute("SELECT 1")
            db_connected = True
            db_msg = f"Connected ({Database.driver})"
        except Exception as e:
            db_msg = str(e)
        self._print_check("Database Connection", db_msg, db_connected)
        
        # 5. Security Configuration Check
        try:
            from config.config import get_config
            cfg = get_config()
            app_debug = str(cfg.get("APP_DEBUG", "false")).lower() in ("true", "1")
            session_secure = str(cfg.get("SESSION_SECURE_COOKIE", "false")).lower() in ("true", "1")
            
            sec_ok = True
            sec_msg = "Secure Configuration"
            if not app_debug and not session_secure:
                sec_ok = False
                sec_msg = "Warning: APP_DEBUG is false, but SESSION_SECURE_COOKIE is false (Should be true in production!)"
            self._print_check("Session Cookie Security Check", sec_msg, sec_ok)
        except Exception as e:
            self._print_check("Session Cookie Security Check", f"Failed checking: {e}", False)
            
        pause()

    def clear_logs(self):
        print(color("\nClear Logs & Temp Files:\n", C_BOLD))
        confirm = input(color("Clear all temporary logs and sessions? (y/N): ", C_YELLOW)).strip().lower()
        if confirm in ["y", "yes"]:
            # Clear logs
            log_dir = os.path.join(PROJECT_ROOT, "storage", "logs")
            session_dir = os.path.join(PROJECT_ROOT, "storage", "sessions")
            
            self._empty_dir(log_dir)
            self._empty_dir(session_dir)
            
            print(color("✓ storage/logs and storage/sessions successfully cleared!", C_GREEN))
        else:
            print("Cancelled.")
        pause()

    def run_migrations(self):
        print(color("\nRunning Database Migrations:\n", C_BOLD))
        try:
            res = subprocess.run([sys.executable, "migrate.py"], capture_output=True, text=True, check=True)
            print(res.stdout)
            print(color("✓ Migrations executed successfully!", C_GREEN))
        except subprocess.CalledProcessError as e:
            print(color(f"✗ Migration failed:\n{e.stderr}", C_RED))
        pause()

    def run_seeders(self):
        print(color("\nRunning Database Seeders:\n", C_BOLD))
        try:
            from core.seeder import Seeder
            Seeder.run_all()
            print(color("\n✓ Seeders executed successfully!", C_GREEN))
        except Exception as e:
            print(color(f"\n✗ Seeding failed: {e}", C_RED))
        pause()

    def run_queue_worker(self):
        print(color("\nRunning Queue Worker (Press Ctrl+C to stop):\n", C_BOLD))
        try:
            # Run the queue worker script using current python executable
            subprocess.run([sys.executable, "queue_worker.py"])
        except KeyboardInterrupt:
            print(color("\nQueue worker stopped.", C_YELLOW))
        except Exception as e:
            print(color(f"\n✗ Worker crashed: {e}", C_RED))
        pause()

    def run_scheduler(self):
        print(color("\nRunning Task Scheduler (Press Ctrl+C to stop):\n", C_BOLD))
        try:
            # Run the scheduler runner script using current python executable
            subprocess.run([sys.executable, "scheduler_runner.py"])
        except KeyboardInterrupt:
            print(color("\nScheduler stopped.", C_YELLOW))
        except Exception as e:
            print(color(f"\n✗ Scheduler crashed: {e}", C_RED))
        pause()

    def run_db_sync(self):
        print(color("\nDatabase Schema Sync Tool:\n", C_BOLD))
        driver = input("Select Driver (1. MySQL, 2. SQLite) [default: 1]: ").strip()
        driver = "sqlite" if driver == "2" else "mysql"

        try:
            from core.db_sync import DBSchemaComparer
            if driver == "sqlite":
                src = input("Source SQLite Path [default: storage/database.sqlite]: ").strip() or "storage/database.sqlite"
                tgt = input("Target SQLite Path [default: storage/database_prod.sqlite]: ").strip() or "storage/database_prod.sqlite"
                res = DBSchemaComparer.compare_sqlite(src, tgt)
            else:
                host = input("MySQL Host [default: 127.0.0.1]: ").strip() or "127.0.0.1"
                port = input("MySQL Port [default: 3306]: ").strip() or "3306"
                user = input("MySQL User [default: root]: ").strip() or "root"
                password = input("MySQL Password [default: None]: ").strip() or ""
                src = input("Source DB [default: pyflow_db]: ").strip() or "pyflow_db"
                tgt = input("Target DB: ").strip()
                if not tgt:
                    print(color("Target DB is required!", C_RED))
                    pause()
                    return
                res = DBSchemaComparer.compare_mysql(host, user, password, src, tgt, port)

            print(color("\nComparison Result Summary:\n", C_BOLD))
            print(f"Total Tables Compared    : {res['summary']['total_tables']}")
            print(f"Missing Tables in Target : {res['summary']['missing_tables_count']}")
            print(f"Mismatched Columns       : {res['summary']['mismatched_columns_count']}")

            if res["generated_sql"]:
                print(color("\nGenerated SQL Upgrade Script:\n", C_GREEN))
                print(res["generated_sql"])
            else:
                print(color("\n✓ Database schemas are completely in sync!", C_GREEN))
        except Exception as e:
            print(color(f"\n✗ Error: {e}", C_RED))
        pause()

    def _get_tables(self):
        tables = []
        if Database.driver == "mysql":
            cursor = Database.execute("SHOW TABLES")
            for row in cursor.fetchall():
                tables.append(list(row.values())[0] if isinstance(row, dict) else row[0])
        else:
            cursor = Database.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            for row in cursor.fetchall():
                tables.append(row[0] if isinstance(row, tuple) else row.get("name") if isinstance(row, dict) else row["name"])
        return tables

    def _print_check(self, label, value, success):
        icon = color(" [PASS] ", C_GREEN) if success else color(" [FAIL] ", C_RED)
        print(f"{label:<30} : {value:<40} {icon}")

    def _empty_dir(self, dir_path):
        if not os.path.exists(dir_path):
            return
        for filename in os.listdir(dir_path):
            file_path = os.path.join(dir_path, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}. Reason: {e}")

    # ─── make: Code Generators ─────────────────────────────────────────────

    def make_migration(self):
        print(color("\nmake:migration — New Migration File\n", C_BOLD))
        name = input(color("Migration name (e.g. create_products_table): ", C_YELLOW)).strip()
        if not name:
            print("Name required!"); pause(); return

        import time
        stubs_dir = os.path.join(PROJECT_ROOT, "stubs")
        stub_path = os.path.join(stubs_dir, "migration.stub")
        timestamp = time.strftime("%Y%m%d%H%M%S")
        file_name = f"{timestamp}_{name}.py"
        out_dir = os.path.join(PROJECT_ROOT, "database", "migrations")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)

        if os.path.exists(stub_path):
            with open(stub_path, "r", encoding="utf-8") as f:
                content = f.read().replace("{{name}}", name).replace("{{class_name}}", "".join(w.capitalize() for w in name.split("_")))
        else:
            table = name.replace("create_", "").replace("_table", "")
            class_name = "".join(w.capitalize() for w in name.split("_"))
            content = f'''# database/migrations/{file_name}


class {class_name}:
    def up(self, cursor, driver):
        """Migration: {name}"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `{table}` (
                id INT AUTO_INCREMENT PRIMARY KEY,
                created_at DATETIME,
                updated_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

    def down(self, cursor, driver):
        """Rollback"""
        cursor.execute("DROP TABLE IF EXISTS `{table}`")
'''
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(color(f"✅ তৈরি হয়েছে: database/migrations/{file_name}", C_GREEN))
        pause()

    def make_job(self):
        print(color("\nmake:job — New Background Job\n", C_BOLD))
        name = input(color("Job class name (e.g. SendEmailJob): ", C_YELLOW)).strip()
        if not name:
            print("Name required!"); pause(); return

        file_name = f"{name[0].lower()}{name[1:]}.py"
        out_dir = os.path.join(PROJECT_ROOT, "app", "jobs")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        if os.path.exists(out_path):
            print(color(f"✗ File already exists: {file_name}", C_RED)); pause(); return

        content = f'''"""app/jobs/{file_name}"""


class {name}:
    """{name} — Background Job"""

    def handle(self, data: dict):
        """
        Job-এর মূল কাজ এখানে লিখুন।
        Queue থেকে call করলে `data` dict হিসেবে পাবেন।
        """
        pass
'''
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(color(f"✅ তৈরি হয়েছে: app/jobs/{file_name}", C_GREEN))
        pause()

    def make_middleware(self):
        print(color("\nmake:middleware — New Middleware\n", C_BOLD))
        name = input(color("Middleware function name (e.g. subscription_middleware): ", C_YELLOW)).strip()
        if not name:
            print("Name required!"); pause(); return

        file_name = f"{name}.py"
        out_dir = os.path.join(PROJECT_ROOT, "app", "middleware")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        if os.path.exists(out_path):
            print(color(f"✗ File already exists: {file_name}", C_RED)); pause(); return

        content = f'''"""app/middleware/{file_name}"""
from core.response import Response


def {name}(request, session):
    """
    Custom Middleware: {name}
    None রিটার্ন করলে পরবর্তী middleware/handler-এ যাবে।
    Response রিটার্ন করলে chain বন্ধ হবে।
    """
    # আপনার middleware logic এখানে লিখুন
    return None
'''
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(color(f"✅ তৈরি হয়েছে: app/middleware/{file_name}", C_GREEN))
        pause()

    def make_seeder(self):
        print(color("\nmake:seeder — New Database Seeder\n", C_BOLD))
        name = input(color("Seeder class name (e.g. ProductSeeder): ", C_YELLOW)).strip()
        if not name:
            print("Name required!"); pause(); return

        file_name = f"{name[0].lower()}{name[1:]}.py"
        out_dir = os.path.join(PROJECT_ROOT, "database", "seeders")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, file_name)
        if os.path.exists(out_path):
            print(color(f"✗ File already exists: {file_name}", C_RED)); pause(); return

        content = f'''"""database/seeders/{file_name}"""


class {name}:
    """Database Seeder: {name}"""

    def run(self):
        """এখানে seed data insert করুন"""
        pass


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from config.config import get_config
    from core.database import Database
    Database.init(get_config())
    {name}().run()
    Database.close()
    print("{name} seed সম্পন্ন!")
'''
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(color(f"✅ তৈরি হয়েছে: database/seeders/{file_name}", C_GREEN))
        pause()

    def run_tests(self):
        print(color("\nUnit Test Suite\n", C_BOLD))
        tests_dir = os.path.join(PROJECT_ROOT, "tests")
        if not os.path.exists(tests_dir):
            print(color("tests/ ফোল্ডার পাওয়া যায়নি। প্রথমে tests/ তৈরি করুন।", C_RED))
            pause(); return
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"],
            cwd=PROJECT_ROOT
        )
        print()
        if result.returncode == 0:
            print(color("✅ সব টেস্ট পাস হয়েছে!", C_GREEN))
        else:
            print(color("✗ কিছু টেস্ট ব্যর্থ হয়েছে।", C_RED))
        pause()

    def flush_cache(self):
        print(color("\nFlush Cache\n", C_BOLD))
        confirm = input(color("সব cache মুছে দিবেন? (yes): ", C_YELLOW)).strip()
        if confirm.lower() != "yes":
            print("বাতিল।"); pause(); return
        from core.cache import Cache
        count = Cache.flush()
        print(color(f"✅ {count}টি cache ফাইল মুছে দেওয়া হয়েছে।", C_GREEN))
        pause()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Non-interactive CLI mode: python cli.py make:migration create_users
        command = sys.argv[1]
        arg = sys.argv[2] if len(sys.argv) > 2 else ""
        cli = PyFlowCLI()
        if command == "make:migration":
            if not arg: print("Usage: python cli.py make:migration <name>"); sys.exit(1)
            # Direct call with arg
            import time
            out_dir = os.path.join(PROJECT_ROOT, "database", "migrations")
            os.makedirs(out_dir, exist_ok=True)
            table = arg.replace("create_", "").replace("_table", "")
            class_name = "".join(w.capitalize() for w in arg.split("_"))
            timestamp = time.strftime("%Y%m%d%H%M%S")
            file_name = f"{timestamp}_{arg}.py"
            content = f'class {class_name}:\n    def up(self, cursor, driver): pass\n    def down(self, cursor, driver): cursor.execute("DROP TABLE IF EXISTS `{table}`")\n'
            with open(os.path.join(out_dir, file_name), "w") as f: f.write(content)
            print(color(f"✅ Created: database/migrations/{file_name}", C_GREEN))
        elif command == "test":
            tests_dir = os.path.join(PROJECT_ROOT, "tests")
            subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py", "-v"], cwd=PROJECT_ROOT)
        elif command == "cache:flush":
            from core.cache import Cache
            count = Cache.flush()
            print(color(f"✅ {count} cache files cleared.", C_GREEN))
        else:
            print(color(f"Unknown command: {command}", C_RED))
    else:
        cli = PyFlowCLI()
        cli.run()
