from typing import Any
from pydantic import BaseModel, BeforeValidator
from typing import Annotated

# Helper to map MongoDB _id to id
PyObjectId = Annotated[str, BeforeValidator(str)]

class MongoBaseModel(BaseModel):
    id: PyObjectId | None = None

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "id": "65b9f9f9f9f9f9f9f9f9f9f9"
            }
        }