from typing import Any, Optional
from pydantic import BaseModel, BeforeValidator, Field
from typing import Annotated

# Helper to map MongoDB _id to id
PyObjectId = Annotated[str, BeforeValidator(str)]

class MongoBaseModel(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_schema_extra = {
            "example": {
                "id": "65b9f9f9f9f9f9f9f9f9f9f9"
            }
        }

    def model_dump(self, **kwargs):
        """
        Exclude _id/id from dump if it is None to allow MongoDB to generate it.
        """
        exclude = kwargs.get("exclude")
        if exclude is None:
            exclude = set()
        elif isinstance(exclude, (list, tuple)):
            exclude = set(exclude)
        
        if self.id is None:
            exclude.add("id")
            
        kwargs["exclude"] = exclude
        return super().model_dump(**kwargs)