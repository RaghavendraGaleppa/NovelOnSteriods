from pydantic import BaseModel, Field
from typing import List, ClassVar, Optional, Type, TypeVar
from datetime import datetime, timedelta

from nos.schemas.mixins import DBFuncMixin

    
T = TypeVar("T", bound="Provider")


class ProviderRateLimitInfo(BaseModel):
    n_requests_made: int = Field(default=0, description="The total number of requests made to the provider")
    n_requests_made_since_last_reset: int = Field(default=0, description="The number of requests made since the last reset of ratelimit")

    is_rate_limited: bool = Field(default=False, description="Whether the provider is rate limited")
    rate_limit_reset_time: datetime = Field(default=datetime.now(), description="The time when the rate limit will be reset")
    
    last_request_time: Optional[datetime] = Field(default=None, description="The time of the last request")


class Provider(DBFuncMixin):

    _collection_name: ClassVar[str] = "providers"
    """ These 3 values should not be updated."""
    url: str
    key: str
    provider: str

    """ These 3 values can be updated """
    name: str
    model_names: List[str]
    priority: int = Field(default=0, description="The priority of the provider. The higher the value, the more weigth it gets")
    
    rate_limit_info: ProviderRateLimitInfo = Field(default=ProviderRateLimitInfo(), description="The rate limit information for the provider")
    
    created_at: datetime = Field(default=datetime.now(), description="The time when the provider was created")
    updated_at: datetime = Field(default=datetime.now(), description="The time when the provider was last updated")
    

    @classmethod
    def load_from_secrets_json(cls: Type[T], secrets_json: dict) -> List[T]:
        providers = []
        for provider in secrets_json["providers"]:
            provider_obj = cls(
                url=provider["url"],
                name=provider["name"],
                key=provider["key"],
                provider=provider["provider"],
                model_names=provider["model_names"],
            )
            providers.append(provider_obj)

        return providers