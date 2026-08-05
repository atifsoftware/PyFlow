class Factory:
    _factories = {}

    @classmethod
    def define(cls, model_class, definition_fn):
        """Define a factory function for a model class"""
        cls._factories[model_class] = definition_fn

    @classmethod
    def build(cls, model_class, overrides=None) -> dict:
        """Build model data without saving to the database"""
        if overrides is None:
            overrides = {}
        if model_class not in cls._factories:
            raise ValueError(f"No factory defined for model: {model_class.__name__}")
        
        data = cls._factories[model_class]()
        data.update(overrides)
        return data

    @classmethod
    def create(cls, model_class, overrides=None, count=1):
        """Build model data and save to the database"""
        if overrides is None:
            overrides = {}
        results = []
        for _ in range(count):
            data = cls.build(model_class, overrides)
            # Support Model's custom create method or create_with_password for User
            if hasattr(model_class, "create_with_password") and "password" in data:
                # User model requires password hashing
                plain_password = data.pop("password")
                instance = model_class.create_with_password(
                    name=data.get("name", "Test User"),
                    email=data.get("email"),
                    plain_password=plain_password,
                    role=data.get("role", "user")
                )
            else:
                instance = model_class.create(data)
            results.append(instance)
        return results[0] if count == 1 else results
