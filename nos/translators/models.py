import json
import yaml
from openai import OpenAI, RateLimitError
from typing import List, Optional, Dict
from pathlib import Path

from nos.config import logger, db
from nos.schemas.secrets_schema import Provider
from nos.schemas.prompt_schemas import PromptSchema
from nos.schemas.translator_schemas import LLMCallResponseSchema
from nos.exceptions.translator_exceptions import LLMNoResponseError, LLMNoUsageError


class Translator:

    def __init__(self, providers: List[Provider]):
        """ Setup the translator """
        self.providers = providers
        self.provider_idx = 0  # We'll start from the beginning
        self.model_idx = 0 # First model in the list
        self.setup_client()
    
    def setup_client(self, provider: Optional[Provider]=None):
        """ Use the internal provider_idx if the provider arg is None"""
        if provider is None:
            provider = self.providers[self.provider_idx]

        self.client = OpenAI(base_url=provider.url, api_key=provider.key)
        self.current_provider = provider
        self.model_idx = 0
        logger.info(f"Done Setting up client for provider: {provider.provider}, name: {provider.name}")


    def call_provider(self, user_prompt: str, system_prompt: Optional[str]=None, temperature: float=0.1, max_tokens: int=2048, raise_usage_error: bool=True, response_format: Optional[Dict]=None):
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

        headers = response.headers
        remaining_req = int(headers.get('x-ratelimit-remaining-requests', -1))
        remaining_tok = int(headers.get('x-ratelimit-remaining-tokens', -1))

        completion = response.parse() # type: ignore


        if completion.choices:
            response_content = completion.choices[0].message.content
            if not response_content:
                raise LLMNoResponseError(self.current_provider, self.model_idx)
            
            if response_format and response_format.get("type") == "json":
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
                remaining_tokens=remaining_tok
            )
        
        raise LLMNoResponseError(self.current_provider, self.model_idx)


    def run_translation(self, text: str, prompt_name: str):

        prompt = PromptSchema.load(db, prompt_name)
        if not prompt:
            raise ValueError(f"Prompt {prompt_name} not found")

        system_prompt = prompt.prompt_content.system_prompt
        user_prompt = prompt.prompt_content.user_prompt
        user_prompt = user_prompt.format(**{"CHINESE_TAGS_JSON_ARRAY": text})
        model_params = prompt.model_parameters

        response = self.call_provider(text, system_prompt, model_params.temperature, model_params.max_tokens)
