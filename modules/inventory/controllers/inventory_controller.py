from core.controller import Controller

class InventoryController(Controller):
    def index(self):
        # Render view using namespace syntax
        return self.view("inventory::dashboard", {
            "title": "Inventory Dashboard",
            "items": ["Laptop", "Monitor", "Keyboard"]
        })
