from bson import ObjectId
from typing import Optional

from nos.config import celery_app, db, logger
from nos.schemas.enums import TranlsationStatus
from nos.schemas.scraping_schema import NovelData
from nos.translators.models import Translator


@celery_app.task
def translate_novel_metadata(novel_id: str):
    """
    Basically translate the metadata of the novel 
    """
    
    novel: Optional[NovelData] = NovelData.load(db=db, query={"_id": ObjectId(novel_id)}) # type: ignore
    
    if novel is None:
        raise Exception(f"Novel {novel_id} not found. Maybe someone deleted it manually?")
    
    logger.info(f"Translating metadata of novel {novel_id}")
        
    t = Translator()

    data = {
        "title_raw": novel.title_raw,
        "author_raw": novel.author_raw,
        "description_raw": novel.description_raw,
    }
    
    translation_metadata = t.run_translation(
        text=data,
        prompt_name="novel_metadata_translation",
        novel_id=novel.id,
    )
    
    if translation_metadata.status == TranlsationStatus.COMPLETED:
        response_content = translation_metadata.llm_call_metadata.response_content
        assert isinstance(response_content, dict)
        novel.title = response_content["title"]
        novel.author = response_content["author"]
        novel.description = response_content["description"]
        novel.all_data_parsed = True
        novel.update(db=db)
        logger.info(f"Translation completed for novel {novel_id}")
    else:
        logger.error(f"Translation failed for novel {novel_id}")
        novel.all_data_parsed = False
        novel.update(db=db)
        raise Exception(f"Translation failed for novel {novel_id}")


    