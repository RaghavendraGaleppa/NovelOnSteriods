from pymongo.database import Database
from bson import ObjectId

class DBFuncMixin:

    _collection_name: str

    def update(self, db: Database):
        # If _id is None, insert it else update it
        collection = db[self._collection_name]
        if self._id is None:
            self._id = collection.insert_one(self.model_dump(exclude={"_id"})).inserted_id # type: ignore
        else:
            collection.update_one(
                {"_id": self._id},
                {"$set": self.model_dump(exclude={"_id"})} # type: ignore
        )

    @classmethod
    def load(cls, db: Database, _id: ObjectId):
        data = db[cls._collection_name].find_one({"_id": _id})
        if data is None:
            raise ValueError(f"Novel with source id {_id} not found")
        return cls(**data)
    