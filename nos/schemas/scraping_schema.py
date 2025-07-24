from typing import List, Optional, ClassVar
from pydantic import BaseModel, Field
from pymongo.database import Database
from bson import ObjectId
from datetime import datetime

from nos.schemas.mixins import DBFuncMixin
from nos.config import logger


class NovelRawData(BaseModel, DBFuncMixin):
    """
    - This will serve as the base schema for all novels. We will use this to load/dump data from and to the db
    """
    class Config:
        arbitrary_types_allowed = True  # This is to ensure ObjectIds work well

    # DB related fields
    _collection_name: ClassVar[str] = "novels" 

    # Info about the novel
    source_name: str  # Basically whether its 1qxs, 69shu or any other source
    novel_source_id: str
    novel_url: str
    chapter_list_url: str
    image_url: str

    # Raw data
    title_raw: str
    author_raw: str
    description_raw: str 
    classification_raw: List[str]
    tags_raw: List[str]
    
    # Metadata
    all_data_parsed: bool = Field(default=False, description="This will be set to True after the raw data is fully translated")
    fingerprint: str

    def update(self, db: Database):
        # If _id is None, insert it else update it
        collection = db[self._collection_name]
        if self.id is None:
            # Check if the fingerprint already exists
            data = collection.find_one({"fingerprint": self.fingerprint})
            if data is not None:
                logger.debug(f"The fingerprint {self.fingerprint} already exists at {data['_id']}")
                self.id = data["_id"]
            else:
                logger.debug(f"The fingerprint {self.fingerprint} does not exist, inserting it")
                self.id = collection.insert_one(self.model_dump(exclude={"id"})).inserted_id # type: ignore
        else:
            collection.update_one(
                {"_id": self.id},
                {"$set": self.model_dump(exclude={"id"})} # type: ignore
        )
    
class NovelData(NovelRawData):

    """ The full data. None basically means that they have not been translated into english """
    title: Optional[str] = Field(default=None, description="This is the translated title of the novel")
    author: Optional[str] = Field(default=None, description="This is the translated author of the novel")
    description: Optional[str] = Field(default=None, description="This is the translated description of the novel")
    classification: Optional[str] = Field(default=None, description="This is the translated classification of the novel")
    tags: Optional[List[str]] = Field(default=None, description="This is the translated tags of the novel")