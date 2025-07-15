from typing import List, Optional, ClassVar
from pydantic import BaseModel, Field
from pymongo.database import Database
from bson import ObjectId

from src.schemas.mixins import DBFuncMixin


class NovelRawData(BaseModel, DBFuncMixin):
    """
    - This will serve as the base schema for all novels. We will use this to load/dump data from and to the db
    """
    # DB related fields
    _id: Optional[ObjectId] = None
    _collection_name: ClassVar[str] = "novels" 

    # Info about the novel
    source_name: str
    novel_source_id: str
    novel_url: str
    chapter_list_url: str

    # Raw data
    title_raw: str
    author_raw: str
    description_raw: str 
    classification_raw: str 
    tags_raw: List[str]
    

    # Metadata
    _all_data_parsed: bool = False  # This will be set to True after the raw data is fully translated


    
class NovelData(NovelRawData):

    """ The full data """
    title: str
    author: str
    description: str
    classification: str
    tags: List[str]