from schemas.secrets_schema import Secrets
from dotenv import load_dotenv
import json
import os

secrets_json_path = os.environ.get("SECRETS_JSON_PATH", "secrets.json")
print(f"Loading secrets from {secrets_json_path}")

with open(secrets_json_path, "r") as f:
    secrets_dict = json.load(f)

secrets = Secrets(**secrets_dict)


with open("src/prompts/NovelDescriptionPrompt-v1.md", "r") as f:
    novel_description_prompt_template = f.read()