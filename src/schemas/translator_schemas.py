import datetime
from pydantic import BaseModel, Field
from mixins import DBFuncMixin




class TranslatorMetadata(BaseModel, DBFuncMixin):
    provider_name: str = Field(description="The name of the api provider through which this translation is taking place")
    model_name: str = Field(description="The name of the model used for this translation")
    start_time: datetime.datetime = Field(description="The start timestamp of translation") 
    end_time: datetime.datetime = Field(description="The end timestamp of translation")
    total_time_taken: datetime.timedelta = Field(description="The total time taken for this translation")
    input_tokens: int = Field(description="The number of tokens used for this translation")
    output_tokens: int = Field(description="The number of tokens used for this translation")
    prompt_version: str = Field(description="Each prompt will have a version associated with it. It can be found in the prompt yaml file")
    prompt_name: str = Field(description="The name of the prompt that was used for this translation. This field can be found in the yaml prompt file")
    
    