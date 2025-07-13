from openai import OpenAI
from schemas.secrets_schema import Secrets
from main import secrets



class Translator:
    def __init__(self, secrets: Secrets):
        self.providers = secrets.providers


    def translate(self, provider_idx: int, text: str):
        pass