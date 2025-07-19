from openai import OpenAI
from schemas.secrets_schema import Provider
from typing import List





class Translator:
    def __init__(self, providers: List[Provider]):
        self.providers = providers
        self.provider_idx = 0
        
    def switch_to_next_provider(self):
        # Rotate from 0 to maxlen of providers
        self.provider_idx = (self.provider_idx + 1) % len(self.providers)
        self.setup_openai_client(self.providers[self.provider_idx])

    def setup_openai_client(self, provider: Provider):
        """ For the given provider, setup an OpenAI client"""
        self.client = OpenAI(api_key=provider.key)

    def translate(self, text: str, prompt_path: str):
        pass
        

    def run_translation_pipeline(self, input_text: str, translation_type: str="chapter", provider_name_preference: str="openai", model_name_preference: str="deepseek/deepseek-chat-v3-0324:free"):
        """ Go through each provider and each model and try to translate text via each provider """
        pass
        