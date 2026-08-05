import os
import importlib.util
import inspect

class Seeder:
    def run(self):
        raise NotImplementedError("Seeder class must implement run method")

    @classmethod
    def run_all(cls):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        seeds_dir = os.path.join(project_root, "app", "database", "seeds")
        
        if not os.path.exists(seeds_dir):
            os.makedirs(seeds_dir, exist_ok=True)
            # Create an empty __init__.py
            with open(os.path.join(seeds_dir, "__init__.py"), "w") as f:
                pass
            print(f"Created seeds directory at: {seeds_dir}")
            return
            
        print("--- Running Database Seeders ---")
        
        # Scan for Python files in alphabetical order
        for filename in sorted(os.listdir(seeds_dir)):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3]
                file_path = os.path.join(seeds_dir, filename)
                
                # Dynamically load module
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                if spec is None or spec.loader is None:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys_modules_key = f"app.database.seeds.{module_name}"
                import sys
                sys.modules[sys_modules_key] = module
                spec.loader.exec_module(module)
                
                # Find classes inheriting from Seeder
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, Seeder) and obj is not Seeder:
                        print(f"Running Seeder: {name} ({filename})...")
                        try:
                            seeder_instance = obj()
                            seeder_instance.run()
                            print(f"[OK] {name} completed successfully.")
                        except Exception as e:
                            print(f"[ERROR] Failed running {name}: {e}")
                            import traceback
                            traceback.print_exc()
