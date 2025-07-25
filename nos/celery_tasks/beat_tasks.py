import json
from pathlib import Path
from typing import List, Optional

from nos.config import celery_app, db, logger
from nos.schemas.enums import TranslationEntityType
from nos.schemas.prompt_schemas import PromptSchema
from nos.schemas.secrets_schema import Provider
from nos.schemas.scraping_schema import NovelData
from nos.schemas.translation_entities_schema import TranslationEntity
from nos.translators.models import Translator


@celery_app.task
def beat_update_tags_of_novels():
    """ This is a beat task that is supposed to run periodically and update the tags for novels."""

    
    # Load all the newly added novels (missing tag field)
    novel_data_records: List[NovelData] = NovelData.load(
        db=db,
        query={
            "tags_raw": {"$exists": True, "$ne": []},
            "$or": [
                {"tags": {"$exists": False}},  # Field doesn't exist
                {"tags": {"$in": [None, []]}}  # Field is None or empty list
            ]
        },
        many=True
    ) # type: ignore
        
    # Get all the unique tags
    all_tags = []
    for nd in novel_data_records:
        all_tags.extend(nd.tags_raw)
    all_tags = set(all_tags)
    
    logger.debug(f"Found {len(novel_data_records)} novels with missing tags")
    logger.debug(f"Found {len(all_tags)} unique tags")
    logger.debug(f"All unique tags: {all_tags}")
        
    # Get all the translated tags
    all_translated_tags: List[TranslationEntity] = TranslationEntity.load(
        db=db,
        query={"type": TranslationEntityType.TAGS.value},
        many=True
    ) # type: ignore

    # Get list of untranslated tags
    translated_keys = set([k.key for k in all_translated_tags])
    translated_kv_pairs = {k.key: k.value for k in all_translated_tags}
    untranslated_keys = list(all_tags - translated_keys)
    
    logger.debug(f"Found {len(untranslated_keys)} untranslated tags")
    logger.debug(f"Untranslated keys: {untranslated_keys}")
    
    untranslated_kv_pairs = {k: None for k in untranslated_keys}

    if len(untranslated_keys) > 0:
        translator = Translator(providers=secrets.providers)
        response = translator.run_translation(untranslated_keys, "tag_translation")
        
        newly_translated_kv_pairs = response.llm_call_metadata.response_content
        # Log this data
        logger.debug(f"Newly translated kv pairs: {newly_translated_kv_pairs}")
        assert isinstance(newly_translated_kv_pairs, dict)
        for k in untranslated_kv_pairs:
            untranslated_kv_pairs[k] = newly_translated_kv_pairs[k]  # Ensure that the key exists. if it doesnot, then let it fail
            
    # create and save the entities
    translation_entities = [{
        "key": k,
        "value": v,
        "type": TranslationEntityType.TAGS
    } for k, v in untranslated_kv_pairs.items()]
    
    for translation_entity in translation_entities:
        translation_entity.update(db=db)
        
    logger.debug(f"Updated {len(translation_entities)} translation entities")

    all_tags_kv_pairs = {**translated_kv_pairs, **untranslated_kv_pairs}
    # We are ensuring that all the untranslate dtags have been translated
    assert all(all_tags_kv_pairs[k] is not None for k in all_tags_kv_pairs)
        
    for nd in novel_data_records:
        # Update the tags for each nd
        nd.tags = []
        for k in nd.tags_raw:
            value = all_tags_kv_pairs[k]
            if value is not None:
                nd.tags.append(value)
        nd.update(db=db)

    logger.debug(f"Updated {len(novel_data_records)} novels with tags")
    
    return all_tags_kv_pairs, untranslated_kv_pairs


@celery_app.task
def beat_update_prompts():
    """ This task will regularly find all the yaml files in the prompts folder, load them in the schema and check if there are fingerprint changes as compared to the db prompts. If there are then, we add the new prompts into the db"""

    prompt_folder = Path(__file__).parent.parent / "prompts"
    for prompt_file in prompt_folder.glob("*.yaml"):
        logger.debug(f"Checking prompt {prompt_file.stem}")
        prompt_from_file = PromptSchema.load(db, query={"prompt_name": prompt_file.stem}, load_from_file=True)
        prompt_from_db = PromptSchema.load(db, query={"prompt_name": prompt_file.stem})

        if prompt_from_file is None:
            logger.debug(f"Prompt {prompt_file.stem} not found in db")
            continue
        if prompt_from_db is None:
            # Directly save the prompt from file to the db
            prompt_from_file.update(db=db)
            logger.debug(f"Prompt {prompt_file.stem} saved to db")
            continue
        
        if prompt_from_file.fingerprint != prompt_from_db.fingerprint:
            logger.debug(f"Prompt {prompt_file.stem} has changed. Updating db")
            prompt_from_file.update(db=db)
            continue
        
        logger.debug(f"Prompt {prompt_file.stem} has not changed. Skipping")



@celery_app.task
def beat_update_providers():
    """ This task will regularly update the providers in the db"""
    secrets_path = Path("secrets.json")
    # Load the secrets
    with open(secrets_path, "r") as f:
        secrets_json = json.load(f)
    providers = Provider.load_from_secrets_json(secrets_json)
    logger.debug(f"Found {len(providers)} providers")
    # Check if the providers exist in the db
    for provider in providers:
        provider_from_db: Optional[Provider] = Provider.load(db, query={"key": provider.key}, many=False) # type: ignore
        if provider_from_db is None:
            provider.update(db=db)
            logger.debug(f"Provider {provider.name} saved to db")
        else:
            # Copy over the values from json to db and update the db
            provider_from_db.model_names = provider.model_names
            provider_from_db.name = provider.name
            provider_from_db.priority = provider.priority
            provider_from_db.update(db=db)
            logger.debug(f"Provider {provider.name} updated in db")
