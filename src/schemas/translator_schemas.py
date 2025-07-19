import datetime
from bson import ObjectId
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

from mixins import DBFuncMixin

class TranlsationStatus(Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"



class TranslatorMetadata(BaseModel, DBFuncMixin):
    _collection_name: str = "translator_metadata"
    
    status: TranlsationStatus = Field(default=TranlsationStatus.STARTED, description="The status of the translation")
    error_message: Optional[str] = Field(default=None, description="The error message if the translation failed. It will remain None if the translation is successfull")

    novel_id: ObjectId = Field(description="The id of the novel that is being translated")

    provider_name: str = Field(description="The name of the api provider through which this translation is taking place")
    model_name: str = Field(description="The name of the model used for this translation")
    prompt_version: str = Field(description="Each prompt will have a version associated with it. It can be found in the prompt yaml file")
    prompt_name: str = Field(description="The name of the prompt that was used for this translation. This field can be found in the yaml prompt file")

    start_time: datetime.datetime = Field(description="The start timestamp of translation") 
    end_time: Optional[datetime.datetime] = Field(default=None, description="The end timestamp of translation")
    total_time_taken: Optional[datetime.timedelta] = Field(default=None, description="The total time taken for this translation")
    input_tokens: Optional[int] = Field(default=None, description="The number of tokens used for this translation")
    output_tokens: Optional[int] = Field(default=None, description="The number of tokens used for this translation")
    
    