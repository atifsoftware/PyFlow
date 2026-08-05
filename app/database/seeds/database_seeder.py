import random
from core.seeder import Seeder
from core.factory import Factory
from app.models.user_model import User
from app.models.setting_model import Setting

class DatabaseSeeder(Seeder):
    def run(self):
        # 1. Define User Factory
        def user_definition():
            rand_id = random.randint(100, 999)
            return {
                "name": f"Dummy User {rand_id}",
                "email": f"user{rand_id}@example.com",
                "password": "password123",
                "role": "user"
            }
        
        Factory.define(User, user_definition)

        # 2. Seed Default Admin User if not exists
        admin = User.find_by("email", "admin@pyflow.com")
        if not admin:
            User.create_with_password(
                name="System Administrator",
                email="admin@pyflow.com",
                plain_password="adminpassword",
                role="admin"
            )
            print("Seeded Default Admin: admin@pyflow.com / adminpassword")
        else:
            print("Admin user already exists.")

        # 3. Seed some Dummy Users using Factory
        print("Seeding 5 dummy users...")
        Factory.create(User, count=5)

        # 4. Seed Default Settings
        settings_to_seed = {
            "site_name": "My PyFlow App",
            "site_description": "A high performance Python MVC application",
            "allow_registration": "true",
            "maintenance_mode": "false"
        }

        for key, val in settings_to_seed.items():
            setting = Setting.find_by("key", key)
            if not setting:
                Setting.create({
                    "key": key,
                    "value": val
                })
                print(f"Seeded Setting: {key} -> {val}")
            else:
                print(f"Setting {key} already exists.")
