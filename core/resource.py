"""
core/resource.py
=================
API Response Transformer (Laravel Resource-এর সমতুল্য)।
Model-এর raw data থেকে নিরাপদ, ফরম্যাটকৃত JSON output তৈরি করে।

ব্যবহার:
    class UserResource(Resource):
        def to_dict(self) -> dict:
            return {
                "id": self.model.id,
                "name": self.model.name,
                "email": self.model.email,
                # password হ্যাশ কখনো include করা হয় না
            }

    # Single resource
    return self.json(UserResource(user).to_response())

    # Collection
    return self.json(UserResource.collection(users))
"""


class Resource:
    """
    Single model-কে API-safe dict-এ রূপান্তর করার জন্য base class।
    Subclass-এ `to_dict()` override করুন।
    """

    def __init__(self, model_or_dict):
        """
        model_or_dict: Model instance অথবা dict
        `self.model` দিয়ে model access করা যাবে।
        """
        if isinstance(model_or_dict, dict):
            # Dict wrapper যাতে attribute access করা যায়
            self.model = _DictWrapper(model_or_dict)
        else:
            self.model = model_or_dict

    def to_dict(self) -> dict:
        """
        Override করুন — API response-এর জন্য field সিলেক্ট করুন।
        Default: model-এর সব non-hidden attribute।
        """
        if hasattr(self.model, "to_dict"):
            return self.model.to_dict()
        elif hasattr(self.model, "_attributes"):
            hidden = set(getattr(self.model.__class__, "hidden", []))
            return {k: v for k, v in self.model._attributes.items() if k not in hidden}
        elif isinstance(self.model, _DictWrapper):
            return dict(self.model._data)
        return {}

    def to_response(self) -> dict:
        """Wrapped response dict রিটার্ন করে — `data` key-এর ভেতরে"""
        return {"data": self.to_dict()}

    @classmethod
    def collection(cls, models: list) -> dict:
        """
        Model-এর list কে resource collection-এ রূপান্তর করে।
        
        ব্যবহার:
            UserResource.collection(User.all())
        """
        return {
            "data": [cls(m).to_dict() for m in models],
            "total": len(models),
        }

    @classmethod
    def paginated(cls, paginator) -> dict:
        """
        Paginator অবজেক্ট থেকে resource collection তৈরি করে pagination meta সহ।
        
        ব্যবহার:
            UserResource.paginated(User.paginate(per_page=15, request=request))
        """
        return {
            "data": [cls(item).to_dict() for item in paginator.items],
            "meta": {
                "current_page": paginator.current_page,
                "last_page": paginator.last_page,
                "per_page": paginator.per_page,
                "total": paginator.total,
                "from": paginator.from_record,
                "to": paginator.to_record,
            },
        }


class _DictWrapper:
    """Dict-কে attribute access করার জন্য wrapper"""
    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, key):
        if key.startswith("_"):
            raise AttributeError(key)
        return self._data.get(key)
