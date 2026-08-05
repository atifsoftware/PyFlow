from core.controller import Controller
from core.decimal_math import Money, MoneyError
from core.database import Database
import time

class FeatureController(Controller):
    def db_status(self):
        try:
            status = Database.get_status()
            return self.json({
                "status": "online",
                "database": status
            })
        except Exception as exc:
            return self.json({"status": "offline", "detail": str(exc)}, status=500)

    def money_convert(self):
        try:
            amount = self.request.input("amount")
            currency = self.request.input("currency", "BDT")
            lang = self.request.input("lang", "bn")
            style = self.request.input("style", "indian")

            m = Money(amount, currency)
            words = m.to_words(lang=lang, style=style)
            return self.json({
                "amount": float(m.amount),
                "currency": m.currency,
                "formatted": m.format(symbol=True),
                "words": words,
                "paisa": m.to_paisa(),
            })
        except MoneyError as exc:
            return self.json({"detail": str(exc)}, status=400)
        except Exception as exc:
            return self.json({"detail": str(exc)}, status=500)

    def transaction_test(self):
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        name = self.request.input("name", "TxUser")
        email = self.request.input("email", "txuser@example.com")
        should_fail = self.request.input("should_fail", False)
        
        if isinstance(should_fail, str):
            should_fail = should_fail.lower() == "true"

        try:
            with Database.transaction():
                from core.query_builder import QueryBuilder
                uid = QueryBuilder("users").insert({
                    "name": name,
                    "email": email,
                    "password": "x",
                    "role": "user",
                    "created_at": now,
                    "updated_at": now,
                })
                
                if should_fail:
                    raise ValueError("ইচ্ছাকৃত এরর — ডাটা রোলব্যাক করা হয়েছে!")
                    
                called_hooks = []
                Database.on_commit(lambda: called_hooks.append("Email sent successfully!"))

            return self.json({
                "status": "success",
                "message": "ট্রানজেকশন সফল ও ডাটা কমিট হয়েছে!",
                "user_id": uid,
                "on_commit_hooks": called_hooks
            })
            
        except Exception as exc:
            from core.query_builder import QueryBuilder
            exists = QueryBuilder("users").where("email", email).exists()
            
            return self.json({
                "status": "rolled_back",
                "message": f"ট্রানজেকশন রোলব্যাক হয়েছে। কারণ: {str(exc)}",
                "exists_in_database": exists
            })
