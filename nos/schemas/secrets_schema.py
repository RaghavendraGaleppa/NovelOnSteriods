from pydantic import BaseModel, Field
from typing import List


class Provider(BaseModel):
    """
    
    """
    url: str
    name: str
    key: str
    provider: str
    model_names: List[str]
    

class Secrets(BaseModel):
    """
    Basically a list of providers
    """
    providers: List[Provider]