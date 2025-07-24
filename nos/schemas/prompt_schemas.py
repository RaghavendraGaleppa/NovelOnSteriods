import yaml
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, TypeVar, Type, Union, List
from pymongo.database import Database

from schemas.mixins import DBFuncMixin

T = TypeVar("T", bound="PromptSchema")

class ModelParameters(BaseModel):
    temperature: float
    max_tokens: int


class PromptContent(BaseModel):
    system_prompt: str
    user_prompt: str

class PromptSchema(BaseModel, DBFuncMixin):
    _collection_name: str = "prompts"

    prompt_name: str
    prompt_version: str
    author: str
    created_date: str
    description: str
    model_parameters: ModelParameters
    prompt_content: PromptContent


    @classmethod
    def load(cls: Type[T], db: Database, prompt_name: str, prompt_version: Optional[str]=None) -> Optional[T]:
        """ 
            The goal is to first check if the db has any prompt with the prompt_name and version. If it does then load it. Otherwise. Load the prompt from the yaml file. Save that to the db and then return the loaded prompt
        """

        query = {"prompt_name": prompt_name}
        if prompt_version is not None:
            query["prompt_version"] = prompt_version

        collection = db[cls._collection_name]
        prompt_record = collection.find_one(query)
        if not prompt_record:
            if prompt_version is not None:
                raise ValueError(f"Prompt {prompt_name} with version {prompt_version} does not exist in db")

            prompt_path = Path(__file__).parent.parent / "prompts" / f"{prompt_name}.yaml"
            with open(prompt_path, "r") as f:
                prompt = yaml.safe_load(f)
            prompt_record = cls(**prompt)
            prompt_record.update(db)

        return prompt_record
        