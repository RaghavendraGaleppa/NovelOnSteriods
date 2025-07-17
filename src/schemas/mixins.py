from pymongo.database import Database
from bson import ObjectId
from typing import Optional

class DBFuncMixin:

    class Config:
        arbitrary_types_allowed = True

    id: Optional[ObjectId] = None
    _collection_name: str

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

    @classmethod
    def load(cls, db: Database, id: ObjectId):
        data = db[cls._collection_name].find_one({"_id": id})
        if data is None:
            raise ValueError(f"Record with id {id} not found")
        return cls(**data)
    