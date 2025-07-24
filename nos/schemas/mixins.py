from bson import ObjectId
from pydantic import Field
from pymongo.database import Database
from typing import Optional, Union, List, Any, TypeVar, Type, ClassVar

T = TypeVar("T", bound="DBFuncMixin")


class DBFuncMixin:

    class Config:
        arbitrary_types_allowed = True

    id: Optional[ObjectId] = Field(default=None, description="The id of the object", alias="_id")
    _collection_name: ClassVar[str]

    def update(self, db: Database):
        # If _id is None, insert it else update it
        collection = db[self._collection_name]
        data_to_dump = {}
        model_fields = self.__class__.model_fields # type: ignore 
        for field_name, field_info in model_fields:
            if field_info.json_schema_extra and field_info.json_schema_extra.get("db_ignore", False):
                continue
            if field_name == "id":
                continue
            data_to_dump[field_name] = getattr(self, field_name)

        if self.id is None:
            self.id = collection.insert_one(data_to_dump).inserted_id # type: ignore
        else:
            collection.update_one(
                {"_id": self.id},
                {"$set": data_to_dump} # type: ignore
        )
            
    def delete(self, db: Database):
        collection = db[self._collection_name]
        collection.delete_one({"_id": self.id})
            
    @classmethod
    def load(cls: Type[T], db: Database, query: dict, many: bool=False) -> Optional[Union[T, List[T]]]:
        if many:
            data = db[cls._collection_name].find(query)
        else:
            data = db[cls._collection_name].find_one(query)
        if not data:
            return None
        
        return cls(**data) if not many else [cls(**item) for item in data] # type: ignore
    