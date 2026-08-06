from core.provider import ServiceProvider
import os

class InventoryServiceProvider(ServiceProvider):
    def register(self):
        # Register view namespace for the module
        views_dir = os.path.join(os.path.dirname(__file__), "views")
        self.app.view_engine.register_namespace("inventory", views_dir)

    def boot(self):
        # Bind module routes to the application router
        router = self.app.router
        from core.controller import action
        from modules.inventory.controllers.inventory_controller import InventoryController
        router.get("/inventory", action(InventoryController, "index"))
