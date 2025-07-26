# Standard library imports
import json
import os
from dotenv import load_dotenv
from datetime import timedelta

# Project imports
from nos.schemas.secrets_schema import Provider
from nos.schemas.config_schemas import DBConfigSchema
from nos.utils.logging_utils import get_logger
from nos.utils.db_utils import get_db_client


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

# Celery setup
from celery import Celery

celery_app = Celery(
    "celery_app",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["nos.celery_tasks.beat_tasks", "nos.celery_tasks.dispatchers", "nos.celery_tasks.tasks"]
)


celery_app.conf.beat_schedule = {
    "beat-tags-translation-and-update": {
        'task': "nos.celery_tasks.beat_tasks.beat_update_tags_of_novels",
        'schedule': timedelta(minutes=1),
    },
    "beat-update-prompts": {
        'task': "nos.celery_tasks.beat_tasks.beat_update_prompts",
        'schedule': timedelta(minutes=1),
    },
    "beat-update-providers": {
        'task': "nos.celery_tasks.beat_tasks.beat_update_providers",
        'schedule': timedelta(minutes=1),
    },
    "dispatch-novel-metadata-translation": {
        'task': "nos.celery_tasks.dispatchers.dispatch_novel_metadata_translation",
        'schedule': timedelta(minutes=5),
    }
}