# Standard library imports
from dotenv import load_dotenv
import json
import os

# Project imports
from src.schemas.secrets_schema import Secrets
from src.schemas.config_schemas import DBConfigSchema
from src.utils.logging_utils import get_logger
from src.utils.db_utils import get_db_client

secrets_json_path = os.environ.get("SECRETS_JSON_PATH", "secrets.json")
print(f"Loading secrets from {secrets_json_path}")

with open(secrets_json_path, "r") as f:
    secrets_dict = json.load(f)

secrets = Secrets(**secrets_dict)
logger = get_logger("main")

logger.info("Starting the main script")

# Load the db
logger.info("Loading the db")
db_config = DBConfigSchema.load()
db = get_db_client(
    host=db_config.host,
    port=db_config.port,
    username=db_config.username,
    pwd=db_config.pwd,
    db_name=db_config.db_name,
    db_auth_source=db_config.db_auth_source
)

with open("src/prompts/NovelDescriptionPrompt-v1.md", "r") as f:
    novel_description_prompt = f.read()
    
