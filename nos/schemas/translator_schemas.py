import datetime
from bson import ObjectId
from pydantic import BaseModel, Field
from typing import Optional, Union, Dict, Annotated

from nos.schemas.mixins import DBFuncMixin
from nos.schemas.enums import TranlsationStatus


class LLMCallResponseSchema(BaseModel):
    """ This schema is not supposed to be stored in the database. It is used to store the response from the llm call """

    response_content: Annotated[
        Union[str, Dict],
        Field(default=None, description="The response content from the llm call", json_schema_extra={"db_ignore": True})
    ]
    input_tokens: Optional[int] = Field(default=None, description="The number of tokens used for this translation")
    output_tokens: Optional[int] = Field(default=None, description="The number of tokens used for this translation")
    remaining_requests: int = Field(description="The number of requests remaining for the current provider")
    remaining_tokens: int = Field(description="The number of tokens remaining for the current provider")
    start_time: datetime.datetime = Field(description="The start timestamp of the llm call")
    end_time: Optional[datetime.datetime] = Field(default=None, description="The end timestamp of the llm call")
    total_time_taken: Optional[datetime.timedelta] = Field(default=None, description="The total time taken for this llm call")

class TranslatorMetadata(BaseModel, DBFuncMixin):
    class Config:
        arbitrary_types_allowed = True  # This is to ensure ObjectIds work well

    _collection_name: str = "translator_metadata"
    
    status: TranlsationStatus = Field(default=TranlsationStatus.STARTED, description="The status of the translation")
    error_message: Optional[str] = Field(default=None, description="The error message if the translation failed. It will remain None if the translation is successfull")

    novel_id: ObjectId = Field(description="The id of the novel that is being translated")
    chapter_id: Optional[ObjectId] = Field(default=None, description="The id of the chapter that is being translated. If the translation is for other things, the novel_id is enough")

    provider_name: str = Field(description="The name of the api provider through which this translation is taking place")
    model_name: str = Field(description="The name of the model used for this translation")
    prompt_id: ObjectId = Field(description="The id of the prompt that was used for this translation")

    llm_call_metadata: LLMCallResponseSchema = Field(description="The metadata for the llm call")

