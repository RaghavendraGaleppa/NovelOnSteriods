from openai import OpenAI
from schemas.secrets_schema import Provider
from typing import List



class Translator:
    def __init__(self, providers: List[Provider], openai_client: OpenAI):
        self.providers = providers
        self.openai_client = openai_client


    def translate(self, provider: Provider, text: str):
        pass
        

    def run_translation_pipeline(self, text: str):
        """ Go through each provider and each model and try to translate text via each provider """
        pass