from typing import List
from pydantic import BaseModel, Field


class Novels(BaseModel):
    """
    - This will serve as the base schema for all novels. We will use this to load/dump data from and to the db
    """
    # Info about the novel
    source_name: str
    novel_source_id: str
    novel_url: str
    novel_list_url: str

    # Raw data
    title_raw: str
    author_raw: str
    description_raw: str 
    classification_raw: str 
    tags_raw: List[str]
    
