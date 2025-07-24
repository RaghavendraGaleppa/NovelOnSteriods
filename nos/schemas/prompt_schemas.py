import yaml
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, TypeVar, Type, Union, List, Dict, Any, ClassVar
from pymongo.database import Database

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
    def load(cls: Type[T], db: Database, prompt_name: str, prompt_version: Optional[str]=None, load_from_file: bool=False) -> Optional[T]:
        """ 
            The goal is to first check if the db has any prompt with the prompt_name and version. If it does then load it. Otherwise. Load the prompt from the yaml file. Save that to the db and then return the loaded prompt
        """

        if not load_from_file:
            query = {"prompt_name": prompt_name}
            if prompt_version is not None:
                query["prompt_version"] = prompt_version

            collection = db[cls._collection_name]
            prompt = collection.find_one(query)
        else:
            if prompt_version is not None:
                raise ValueError(f"Prompt {prompt_name} with version {prompt_version} does not exist in db")

            prompt_path = Path(__file__).parent.parent / "prompts" / f"{prompt_name}.yaml"
            with open(prompt_path, "r") as f:
                prompt = yaml.safe_load(f)
                prompt["fingerprint"] = get_file_hash(prompt_path)
                
        if not prompt or not isinstance(prompt, dict):
            raise ValueError(f"Prompt {prompt_name} with version {prompt_version} does not exist in db or file")

        prompt_record = cls(**prompt)
        return prompt_record
        