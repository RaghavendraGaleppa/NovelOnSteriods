from pymongo.database import Database
from bson import ObjectId
from typing import Optional, Union, List, Any, TypeVar, Type, ClassVar

T = TypeVar("T", bound="DBFuncMixin")


class DBFuncMixin:

    class Config:
        arbitrary_types_allowed = True

    id: Optional[ObjectId] = None
    _collection_name: ClassVar[str]

    def update(self, db: Database):
        # If _id is None, insert it else update it
        collection = db[self._collection_name]
        if self.id is None:
            self.id = collection.insert_one(self.model_dump(exclude={"_id"})).inserted_id # type: ignore
        else:
            collection.update_one(
                {"_id": self.id},
                {"$set": self.model_dump(exclude={"_id"})} # type: ignore
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
    