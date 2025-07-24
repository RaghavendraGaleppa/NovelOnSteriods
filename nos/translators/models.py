import time
import json
import yaml
import httpx
import datetime
from bson import ObjectId
from openai import OpenAI, RateLimitError
from typing import List, Optional, Dict, Union
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception, RetryCallState

from nos.config import logger, db
from nos.schemas.secrets_schema import Provider
from nos.schemas.prompt_schemas import PromptSchema
from nos.schemas.translator_schemas import LLMCallResponseSchema, TranslatorMetadata
from nos.schemas.enums import TranlsationStatus
from nos.exceptions.translator_exceptions import LLMNoResponseError, LLMNoUsageError


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

    def __init__(self, providers: List[Provider]):
        """ Setup the translator """
        self.providers = providers
        self.provider_idx = 0  # We'll start from the beginning
        self.model_idx = 0 # First model in the list
        self.setup_client()


    def switch_providers(self):
        self.provider_idx = (self.provider_idx + 1) % len(self.providers)
        self.model_idx = 0
        self.setup_client()
    
    def setup_client(self, provider: Optional[Provider]=None):
        """ Use the internal provider_idx if the provider arg is None"""
        if provider is None:
            provider = self.providers[self.provider_idx]

        self.client = OpenAI(base_url=provider.url, api_key=provider.key)
        self.current_provider = provider
        self.model_idx = 0
        logger.info(f"Done Setting up client for provider: {provider.provider}, name: {provider.name}")

    
    def call_provider(self, user_prompt: str, system_prompt: Optional[str]=None, temperature: float=0.1, max_tokens: int=2048, response_format: Optional[Dict]=None, raise_usage_error: bool=True):
        """ Send the text to llm and return response """
        model_name = self.current_provider.model_names[self.model_idx]
        logger.debug(f"Calling provider: {self.current_provider.provider}, model: {model_name}")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        start_time = datetime.datetime.now()
        response = self.client.chat.completions.with_raw_response.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format # type: ignore
        )

        headers = response.headers
        remaining_req = int(headers.get('x-ratelimit-remaining-requests', -1))
        remaining_tok = int(headers.get('x-ratelimit-remaining-tokens', -1))

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
                start_time=start_time,
            )
        
        raise LLMNoResponseError(self.current_provider, self.model_idx)


    def run_translation(self, text: Union[str, List, Dict], prompt_name: str, novel_id: Optional[ObjectId]=None, chapter_id: Optional[ObjectId]=None):

        prompt = PromptSchema.load(db, prompt_name)
        if not prompt:
            raise ValueError(f"Prompt {prompt_name} not found")

        system_prompt = prompt.prompt_content.system_prompt
        user_prompt = prompt.prompt_content.user_prompt
        user_prompt = user_prompt.format(**{"CHINESE_TAGS_JSON_ARRAY": text})
        model_params = prompt.model_parameters
        status = TranlsationStatus.STARTED

        n_tries = 0
        while True:
            if n_tries > 10:
                logger.info(f"Failed to get response after {n_tries} tries. Skipping this translation")
                status = TranlsationStatus.FAILED
                error_message = f"Failed to get response after {n_tries} tries"
                break
            try:
                logger.debug(f"Calling provider: {self.current_provider.name}, model: {self.current_provider.model_names[self.model_idx]}, attempt: {n_tries}")
                response: LLMCallResponseSchema = self.call_provider(user_prompt, system_prompt, model_params.temperature, model_params.max_tokens, response_format=model_params.response_format)
                response.end_time = datetime.datetime.now()
                response.total_time_taken = (response.end_time - response.start_time).total_seconds() if response.start_time else None
                status = TranlsationStatus.COMPLETED
                error_message = None
                break
            except RateLimitError as re:
                n_tries += 1
                logger.info(f"Rate limited for {self.current_provider.name}. Attempt number: {n_tries}")
                self.switch_providers()
                time.sleep(2)
                continue

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
        logger.debug(f"{translator_metadata.model_dump()=}")
        translator_metadata.update(db)
        return translator_metadata