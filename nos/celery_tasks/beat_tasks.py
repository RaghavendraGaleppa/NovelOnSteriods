import json
from typing import List

from nos.config import celery_app, db, secrets, logger
from nos.schemas.enums import TranslationEntityType
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