from openai import OpenAI, RateLimitError
from typing import List, Optional
from pathlib import Path
import yaml

from nos.config import logger
from nos.schemas.secrets_schema import Provider
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


    def call_provider(self, text: str, system_prompt: Optional[str]=None, temperature: float=0.1, max_tokens: int=2048, raise_usage_error: bool=True):
        """ Send the text to llm and return response """
        model_name = self.current_provider.model_names[self.model_idx]
        logger.debug(f"Calling provider: {self.current_provider.provider}, model: {model_name}")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": text})


        response = self.client.chat.completions.with_raw_response.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        headers = response.headers
        remaining_req = headers.get('x-ratelimit-remaining-requests')
        remaining_tok = headers.get('x-ratelimit-remaining-tokens')

        completion = response.parse() # type: ignore


        if completion.choices:
            response_content = completion.choices[0].message.content
            if not response_content:
                raise LLMNoResponseError(self.current_provider, self.model_idx)
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
                response_text=response_content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                remaining_requests=remaining_req,
                remaining_tokens=remaining_tok
            )
        
        raise LLMNoResponseError(self.current_provider, self.model_idx)


    def run_translation(self, text: str, prompt_name: str):

        # Load the prompt
        prompt_path = Path(__file__).parent.parent / "prompts" / f"{prompt_name}.yaml"
        with open(prompt_path, "r") as f:
            prompt = yaml.safe_load(f)
