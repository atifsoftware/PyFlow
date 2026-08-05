from core.controller import Controller
from core.db_sync import DBSchemaComparer

class DBSyncController(Controller):
    def index(self):
        # Only admin can access
        if self.session.get("role") != "admin":
            return self.back_with_errors({"error": ["আপনার এই পেজে ঢোকার অনুমতি নেই।"]})
            
        return self.view("admin.db_sync")

    def compare(self):
        if self.session.get("role") != "admin":
            return self.json({"status": "error", "message": "আপনার এই অ্যাকশন করার অনুমতি নেই।"}, status=403)
            
        driver = self.request.input("driver", "mysql")
        
        try:
            if driver == "sqlite":
                src_db = self.request.input("src_db")
                tgt_db = self.request.input("tgt_db")
                if not src_db or not tgt_db:
                    return self.json({"status": "error", "message": "Both Source and Target SQLite paths are required."})
                res = DBSchemaComparer.compare_sqlite(src_db, tgt_db)
            else:
                host = self.request.input("host", "localhost")
                user = self.request.input("user", "root")
                password = self.request.input("pass", "")
                src_db = self.request.input("src_db")
                tgt_db = self.request.input("tgt_db")
                port = self.request.input("port", "3306")
                if not src_db or not tgt_db:
                    return self.json({"status": "error", "message": "Both Source and Target databases are required."})
                res = DBSchemaComparer.compare_mysql(host, user, password, src_db, tgt_db, port)
                
            return self.json(res)
        except Exception as e:
            return self.json({"status": "error", "message": f"Error: {str(e)}"})
