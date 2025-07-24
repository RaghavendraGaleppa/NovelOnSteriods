from typing import List

from nos.config import celery_app, db, secrets
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
            "tags_raw": {"$exists": True},
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

        
    # Get all the translated tags
    all_translated_tags: List[TranslationEntity] = TranslationEntity.load(
        db=db,
        query={"type": TranslationEntityType.TAGS},
        many=True
    ) # type: ignore

    # Get list of untranslated tags
    translated_keys = set([k.key for k in all_translated_tags])
    translated_kv_pairs = {k.key: k.value for k in all_translated_tags}
    untranslated_keys = list(all_tags - translated_keys)
    
    untranslated_kv_pairs = {k: None for k in untranslated_keys}
    all_tags_kv_pairs = {**translated_kv_pairs, **untranslated_kv_pairs}

    if len(untranslated_keys) > 0:
        translator = Translator(providers=secrets.providers)
        

        
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

    

