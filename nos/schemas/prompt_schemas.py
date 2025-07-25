import yaml
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, TypeVar, Type, Union, List, Dict, Any, ClassVar
from pymongo.database import Database

from nos.config import logger
from nos.utils.file_utils import get_file_hash


from nos.schemas.mixins import DBFuncMixin

T = TypeVar("T", bound="PromptSchema")


class ModelParameters(BaseModel):
    temperature: float
    max_tokens: int
    response_format: Optional[Dict[str, str]] = None


class PromptContent(BaseModel):
    system_prompt: str
    user_prompt: str

class PromptSchema(DBFuncMixin):


    _collection_name: ClassVar[str] = "prompts"

    prompt_name: str
    prompt_version: str
    author: str
    created_date: str
    description: str
    model_parameters: ModelParameters
    prompt_content: PromptContent
    
    fingerprint: str

    @classmethod
    def load(cls: Type[T], db: Database, query: Optional[Dict[str, Any]]=None, load_from_file: bool=False) -> Optional[T]:
        """ 
        - If load from file is true then the query must only contain the prompt_name
        """

        if query is None:
            raise ValueError("Query is required when load_from_file is false")
        if not load_from_file:
            collection = db[cls._collection_name]
            try:
                prompt = collection.find(query).sort("_id", -1).limit(1).next()
            except StopIteration:
                logger.debug(f"No prompt found for query {query} in db")
                return None
        else:
            if "prompt_name" not in query:
                raise ValueError("prompt_name is required when load_from_file is true")

            prompt_path = Path(__file__).parent.parent / "prompts" / f"{query['prompt_name']}.yaml"
            with open(prompt_path, "r") as f:
                prompt = yaml.safe_load(f)
                prompt["fingerprint"] = get_file_hash(prompt_path)
                
        if not prompt or not isinstance(prompt, dict):
            raise ValueError(f"Prompt with query {query} does not exist in db or file")

        prompt_record = cls(**prompt)
        return prompt_record
        