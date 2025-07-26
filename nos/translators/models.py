import time
import json
import yaml
import httpx
import datetime
import backoff
from bson import ObjectId
from openai import OpenAI, RateLimitError
from typing import List, Optional, Dict, Union
from pathlib import Path

from nos.config import logger, db
from nos.schemas.secrets_schema import Provider
from nos.schemas.prompt_schemas import PromptSchema
from nos.schemas.translator_schemas import LLMCallResponseSchema, TranslatorMetadata
from nos.schemas.enums import TranlsationStatus
from nos.exceptions.translator_exceptions import LLMNoResponseError, LLMNoUsageError, NoProvidersAvailable


def mock_rate_limit():
    mock_request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    
    # Create a mock response object that looks like a real rate limit error
    mock_response = httpx.Response(
        status_code=429,
        request=mock_request, # Attach the mock request to the response
        json={"error": {"message": "You exceeded your current quota, please check your plan and billing details."}}
    )
    
    # Manually raise the RateLimitError with the properly constructed mock response
    raise RateLimitError(
        message="Simulated Rate Limit Error for testing.",
        response=mock_response,
        body=None
    )

class Translator:

    def __init__(self):
        """ Setup the translator """
        self.switch_providers()
        self.setup_client()


    def switch_providers(self, mark_current_provider_as_exhausted: bool=False):
        """
        1. Load all the providers whose rate_limit_info.rate_limit_reset_time is in the past
        2. These providers must be sorted by priority high to low
        3. If there are no providers to switch to, raise an error
        4. Set the current provider to the first provider in the list
        5. Setup the client for the new provider
        6. Return the new provider
        """
        # Mark the current provider as exhausted
        if hasattr(self, "current_provider") and mark_current_provider_as_exhausted is True:
            self.mark_current_provider_as_exhausted()

        # Load all the providers fromt the db
        logger.debug(f"Switching providers")
        providers: List[Provider] = Provider.load(db, query={"rate_limit_info.rate_limit_reset_time": {"$lt": datetime.datetime.now()}}, many=True) # type: ignore
        if not providers:
            raise NoProvidersAvailable()
        
        logger.debug(f"Found {len(providers)} providers to switch to")
        # Sort the providers by priority high to low
        providers.sort(key=lambda x: x.priority, reverse=True)
        
        # Set the current provider to the first provider in the list
        self.current_provider = providers[0]
        self.setup_client(self.current_provider)
        
        # Return the new provider
        return self.current_provider
    

    def mark_current_provider_as_exhausted(self):
        logger.debug(f"Marking current provider as exhausted: {self.current_provider.model_dump()=}")
        self.current_provider.rate_limit_info.rate_limit_reset_time = datetime.datetime.now() + datetime.timedelta(days=1)
        self.current_provider.rate_limit_info.n_requests_made_since_last_reset = 0
        self.current_provider.rate_limit_info.is_rate_limited = True
        self.current_provider.update(db)
        

    def mark_current_provider_use(self):
        self.current_provider.rate_limit_info.n_requests_made += 1
        self.current_provider.rate_limit_info.n_requests_made_since_last_reset += 1
        self.current_provider.rate_limit_info.is_rate_limited = False
        self.current_provider.rate_limit_info.last_request_time = datetime.datetime.now()
        self.current_provider.update(db)
        pass
        
    
    def setup_client(self, provider: Optional[Provider]=None):
        """ Use the internal provider_idx if the provider arg is None"""
        if provider is None:
            provider = self.current_provider

        self.client = OpenAI(base_url=provider.url, api_key=provider.key)
        self.current_provider = provider
        self.model_idx = 0
        logger.info(f"Done Setting up client for provider: {provider.provider}, name: {provider.name}")

    @backoff.on_exception(
            backoff.constant,
            RateLimitError,
            interval=2,
            on_backoff=lambda details: details['args'][0].switch_providers(mark_current_provider_as_exhausted=True)
    )
    def call_provider(self, user_prompt: str, system_prompt: Optional[str]=None, temperature: float=0.1, max_tokens: int=2048, response_format: Optional[Dict]=None, raise_usage_error: bool=True):
        """ Send the text to llm and return response """
        model_name = self.current_provider.model_names[self.model_idx]
        logger.debug(f"Calling provider: {self.current_provider.provider}, model: {model_name}")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        response = self.client.chat.completions.with_raw_response.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format # type: ignore
        )
        self.mark_current_provider_use()
        headers = response.headers
        remaining_req = int(headers.get('x-ratelimit-remaining-requests', -1))
        remaining_tok = int(headers.get('x-ratelimit-remaining-tokens', -1))
        
        logger.debug(f"Response headers: {headers}")

        completion = response.parse() # type: ignore


        if completion.choices:
            response_content = completion.choices[0].message.content
            if not response_content:
                raise LLMNoResponseError(self.current_provider, self.model_idx)
            
            if response_format and response_format.get("type") == "json_object":
                response_content = json.loads(response_content)
            if completion.usage:
                input_tokens = completion.usage.prompt_tokens
                output_tokens = completion.usage.completion_tokens
            else:
                if raise_usage_error:
                    raise LLMNoUsageError(self.current_provider, self.model_idx)
                else:
                    input_tokens = None
                    output_tokens = None

            return LLMCallResponseSchema(
                response_content=response_content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                remaining_requests=remaining_req,
                remaining_tokens=remaining_tok,
            )
        
        raise LLMNoResponseError(self.current_provider, self.model_idx)


    def run_translation(self, text: Union[str, List, Dict], prompt_name: str, novel_id: Optional[ObjectId]=None, chapter_id: Optional[ObjectId]=None):

        prompt = PromptSchema.load(db, query={"prompt_name": prompt_name})
        if not prompt:
            raise ValueError(f"Prompt {prompt_name} not found")

        system_prompt = prompt.prompt_content.system_prompt
        user_prompt = prompt.prompt_content.user_prompt
        user_prompt = user_prompt.format(**{"INPUT_DATA": text})
        model_params = prompt.model_parameters
        status = TranlsationStatus.STARTED

        logger.debug(f"Calling provider: {self.current_provider.name}, model: {self.current_provider.model_names[self.model_idx]}")
        start_time = datetime.datetime.now()
        response = LLMCallResponseSchema(**{})  # Just create and keep an empty schema
        try:
            response: LLMCallResponseSchema = self.call_provider(user_prompt, system_prompt, model_params.temperature, model_params.max_tokens, response_format=model_params.response_format)
            status = TranlsationStatus.COMPLETED
            error_message = None
        except NoProvidersAvailable as re:
            logger.info(f"No providers available to switch to")
            # Set the status to failed
            status = TranlsationStatus.FAILED
            error_message = f"No providers available to switch to"
            response = LLMCallResponseSchema(**{"start_time": start_time, "end_time": datetime.datetime.now(), "total_time_taken": (datetime.datetime.now() - start_time).total_seconds()})
        finally:
            response.start_time = start_time
            response.end_time = datetime.datetime.now()
            response.total_time_taken = (response.end_time - response.start_time).total_seconds() 

        translator_metadata = {
            "status": status,
            "error_message": error_message,
            "novel_id": novel_id,
            "chapter_id": chapter_id,
            "provider_name": self.current_provider.name,
            "model_name": self.current_provider.model_names[self.model_idx],
            "prompt_id": prompt.id,
            "llm_call_metadata": response
        }
        # Print the translator metadata
        translator_metadata = TranslatorMetadata(**translator_metadata)
        translator_metadata.update(db)
        # Log the amount of time it took
        logger.info(f"Translation completed in {response.total_time_taken} seconds")
        return translator_metadata