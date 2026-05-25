from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, model_validator


class MongoModel(BaseModel):
    """Base model for Pydantic schemas populated from MongoDB documents.

    Coerces ``ObjectId`` → ``str`` and ``datetime`` → ISO strings, and ignores
    extra fields so that ``model_validate(doc)`` works directly on a
    MongoDB cursor result.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def _coerce_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, datetime):
                    data[k] = v.isoformat()
                elif isinstance(v, ObjectId):
                    data[k] = str(v)
        return data
