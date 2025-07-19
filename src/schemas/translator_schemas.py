import datetime
from pydantic import BaseModel, Field




class TranslatorMetadata(BaseModel):
    provider_name: str = Field(description="The name of the api provider through which this translation is taking place")
    model_name: str = Field(description="The name of the model used for this translation")
    start_time: datetime.datetime = Field(description="The start timestamp of translation") 
    end_time: datetime.datetime = Field(description="The end timestamp of translation")
    total_time_taken: datetime.timedelta = Field(description="The total time taken for this translation")
    input_tokens: int = Field(description="The number of tokens used for this translation")
    output_tokens: int = Field(description="The number of tokens used for this translation")
    translation_type: str = Field(description="The type of translation that is taking place")
    prompt_version: str = Field(description="Each prompt will have a version associated with it. This is the version of the prompt that was used for this translation")
    
    
class TranslatorOutput(BaseModel):
    translator_metadata: TranslatorMetadata = Field(description="The metadata for this translation")
