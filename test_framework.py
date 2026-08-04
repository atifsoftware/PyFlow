import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database import Database
from config.config import get_config
from core.validator import Validator
from app.models.user_model import User

# Initialize database
config = get_config()
Database.init(config)

print("--- Testing Form Validation Engine ---")
# Test validator logic
test_data = {
    "name": "   ",  # will fail required after strip
    "email": "invalid-email",
    "password": "123",
    "role": "user"
}

rules = {
    "name": "required|min:3",
    "email": "required|email",
    "password": "required|min:6"
}

validator = Validator(test_data, rules)
print("Validation failed (should be True):", validator.fails())
print("Validation errors:", validator.errors())

# Test Database Nested Transaction
print("\n--- Testing Database Nested Transactions ---")
try:
    with Database.transaction():
        print("Outermost transaction started. Level:", getattr(Database._local, "transaction_level", 0))
        
        # Create a user in outermost transaction
        user = User.create_with_password(
            name="Outer User",
            email="outer@example.com",
            plain_password="password123",
            role="user"
        )
        print("Outer User created with ID:", user.id)

        try:
            with Database.transaction():
                print("Inner/Nested transaction started. Level:", getattr(Database._local, "transaction_level", 0))
                # Create another user in inner transaction
                inner_user = User.create_with_password(
                    name="Inner User",
                    email="inner@example.com",
                    plain_password="password123",
                    role="user"
                )
                print("Inner User created with ID:", inner_user.id)
                
                # Force failure in nested transaction
                print("Forcing exception in inner transaction...")
                raise ValueError("Inner transaction failed intentionally")
        except ValueError as e:
            print("Caught expected exception in nested transaction:", e)
            print("Level after nested exception:", getattr(Database._local, "transaction_level", 0))

        # Check if the outer transaction can continue and commit
        print("Committing outer transaction...")
except Exception as e:
    print("Unexpected exception in outer transaction:", e)

# Clean up: print all users to see if Outer User is present but Inner User was rolled back
print("\nUsers currently in database:")
for u in User.all():
    print(f"- {u.name} ({u.email})")

# Clean up outer@example.com if exists
outer_user = User.find_by("email", "outer@example.com")
if outer_user:
    outer_user.delete()
    print("Cleaned up outer user.")
